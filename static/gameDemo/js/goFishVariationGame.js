(function () {
  const RANKS = ["A", "K", "Q", "J", "10", "9", "8", "7", "6", "5", "4", "3", "2"];
  const SUITS = ["hearts", "diamonds", "clubs", "spades"];

  function createDeck() {
    const deck = [];
    let id = 0;
    for (let s = 0; s < SUITS.length; s += 1) {
      for (let r = 0; r < RANKS.length; r += 1) {
        deck.push({ rank: RANKS[r], suit: SUITS[s], id: id });
        id += 1;
      }
    }
    for (let i = deck.length - 1; i > 0; i -= 1) {
      const j = Math.floor(Math.random() * (i + 1));
      const tmp = deck[i];
      deck[i] = deck[j];
      deck[j] = tmp;
    }
    return deck;
  }

  function getHand(player) {
    if (!player.facedown_cards) {
      player.facedown_cards = {};
    }
    if (!Array.isArray(player.facedown_cards.hand)) {
      player.facedown_cards.hand = [];
    }
    if (!player.private) {
      player.private = {};
    }
    player.private.hand = player.facedown_cards.hand;
    return player.facedown_cards.hand;
  }

  function checkAndRevealBooks(state, playerId, logger) {
    const player = state.players[playerId];
    const hand = getHand(player);
    const counts = {};

    for (let i = 0; i < hand.length; i += 1) {
      const rank = hand[i].rank;
      counts[rank] = (counts[rank] || 0) + 1;
    }

    Object.keys(counts).forEach(function (rank) {
      if (counts[rank] !== 4) {
        return;
      }
      const books = state.common.faceup_cards.books_collected[playerId];
      if (books.indexOf(rank) !== -1) {
        return;
      }
      books.push(rank);
      player.public.revealed_books.push(rank);
      const kept = hand.filter(function (card) {
        return card.rank !== rank;
      });
      player.facedown_cards.hand = kept;
      player.private.hand = kept;
      logger.info("Player " + playerId + " has collected a book of '" + rank + "'s.");
    });
  }

  function determineWinners(state) {
    const books = state.common.faceup_cards.books_collected;
    let maxBooks = -1;
    const winners = [];
    Object.keys(books).forEach(function (pidStr) {
      const pid = Number(pidStr);
      const count = books[pid].length;
      if (count > maxBooks) {
        maxBooks = count;
      }
    });
    Object.keys(books).forEach(function (pidStr) {
      const pid = Number(pidStr);
      if (books[pid].length === maxBooks) {
        winners.push(pid);
      }
    });
    return winners;
  }

  function checkGameOver(state, logger) {
    const books = state.common.faceup_cards.books_collected;
    let totalBooks = 0;
    Object.keys(books).forEach(function (pidStr) {
      totalBooks += books[Number(pidStr)].length;
    });

    if (totalBooks === 13) {
      state.common.is_over = true;
      logger.info("All books have been collected. The game is over.");
      return;
    }

    if (state.common.facedown_cards.stock.length > 0) {
      return;
    }

    for (let i = 0; i < state.common.num_players; i += 1) {
      checkAndRevealBooks(state, i, logger);
    }
    state.common.is_over = true;
    logger.info("Stockpile exhausted, game ends.");
    const winners = determineWinners(state);
    logger.info("Player(s) " + winners.join(" and ") + " win(s).");
  }

  class GoFishVariationGame {
    constructor() {
      this.name = "Go Fish: Misdirection";
      this.recommendedPlayers = 4;
      this.numPlayersRange = [2, 3, 4, 5];
    }

    getConfig() {
      return {
        recommendedNumPlayers: this.recommendedPlayers,
        numPlayersRange: this.numPlayersRange.slice(),
      };
    }

    initState(config, logger) {
      const numPlayers = Number(config.numPlayers) || this.recommendedPlayers;
      const state = {
        common: {
          num_players: numPlayers,
          current_player: 0,
          is_over: false,
          facedown_cards: {
            stock: createDeck(),
          },
          faceup_cards: {
            books_collected: {},
            turn_actions: [],
          },
        },
        players: [],
      };

      for (let i = 0; i < numPlayers; i += 1) {
        state.common.faceup_cards.books_collected[i] = [];
        state.players.push({
          public: { revealed_books: [] },
          faceup_cards: {},
          facedown_cards: { hand: [] },
          private: { hand: [] },
        });
      }

      const cardsPerPlayer = numPlayers <= 3 ? 7 : 5;
      logger.info("Dealing " + cardsPerPlayer + " cards to each of " + numPlayers + " players.");
      for (let p = 0; p < numPlayers; p += 1) {
        const hand = getHand(state.players[p]);
        for (let c = 0; c < cardsPerPlayer; c += 1) {
          const card = state.common.facedown_cards.stock.pop();
          if (card) {
            hand.push(card);
          }
        }
      }

      for (let p = 0; p < numPlayers; p += 1) {
        checkAndRevealBooks(state, p, logger);
      }

      return state;
    }

    applyAction(state, action, logger) {
      if (!action || action.action !== "request" || !action.args) {
        logger.info("Invalid action ignored.");
        return state;
      }

      const currentPlayer = state.common.current_player;
      const targetPlayer = Number(action.args.target_player);
      const requestedRank = String(action.args.rank);

      if (targetPlayer === currentPlayer || targetPlayer < 0 || targetPlayer >= state.common.num_players) {
        logger.info("Invalid target player ignored.");
        return state;
      }

      const requesterHand = getHand(state.players[currentPlayer]);
      const targetHand = getHand(state.players[targetPlayer]);

      logger.info("Player " + currentPlayer + " requests " + requestedRank + " from Player " + targetPlayer + ".");

      const transferred = targetHand.filter(function (card) {
        return card.rank === requestedRank;
      });

      if (transferred.length > 0) {
        const kept = targetHand.filter(function (card) {
          return card.rank !== requestedRank;
        });
        state.players[targetPlayer].facedown_cards.hand = kept;
        state.players[targetPlayer].private.hand = kept;
        for (let i = 0; i < transferred.length; i += 1) {
          requesterHand.push(transferred[i]);
        }
        state.common.faceup_cards.turn_actions.push({
          requester: currentPlayer,
          target: targetPlayer,
          rank: requestedRank,
          result: "success",
          count: transferred.length,
        });
        logger.info(
          "Player " +
            targetPlayer +
            " gives " +
            transferred.length +
            " '" +
            requestedRank +
            "' card(s) to Player " +
            currentPlayer +
            "."
        );
        checkAndRevealBooks(state, currentPlayer, logger);
      } else {
        state.common.faceup_cards.turn_actions.push({
          requester: currentPlayer,
          target: targetPlayer,
          rank: requestedRank,
          result: "fail",
          count: 0,
        });
        logger.info("Player " + targetPlayer + " has no '" + requestedRank + "' card. Go Fish!");
        if (state.common.facedown_cards.stock.length > 0) {
          const drawn = state.common.facedown_cards.stock.pop();
          requesterHand.push(drawn);
          logger.info("Player " + currentPlayer + " draws a card from stock.");
          checkAndRevealBooks(state, currentPlayer, logger);
        } else {
          logger.info("The stockpile is empty. No card drawn.");
        }
        state.common.current_player = (currentPlayer + 1) % state.common.num_players;
      }

      checkGameOver(state, logger);
      return state;
    }

    getLegalActions(state, playerId) {
      if (state.common.is_over) {
        return [];
      }
      const currentPlayer = Number.isInteger(playerId) ? playerId : state.common.current_player;
      const legal = [];
      for (let target = 0; target < state.common.num_players; target += 1) {
        if (target === currentPlayer) {
          continue;
        }
        for (let i = 0; i < RANKS.length; i += 1) {
          legal.push({
            action: "request",
            args: {
              target_player: target,
              rank: RANKS[i],
            },
          });
        }
      }
      return legal;
    }

    getPayoffs(state, logger) {
      const books = state.common.faceup_cards.books_collected;
      let maxBooks = -1;
      for (let i = 0; i < state.common.num_players; i += 1) {
        maxBooks = Math.max(maxBooks, books[i].length);
      }

      const payoffs = [];
      for (let i = 0; i < state.common.num_players; i += 1) {
        const count = books[i].length;
        if (count === maxBooks) {
          payoffs.push(0);
          logger.info("Player " + i + " has the highest number of books: " + count + ".");
        } else {
          payoffs.push(count - maxBooks);
          logger.info("Player " + i + " has " + count + " books.");
        }
      }
      return payoffs;
    }
  }

  class GoFishVariationEngine extends window.BaseCardGameEngine {
    constructor(config = {}) {
      super(new GoFishVariationGame(), config);
    }
  }

  window.GoFishVariationEngine = GoFishVariationEngine;
})();
