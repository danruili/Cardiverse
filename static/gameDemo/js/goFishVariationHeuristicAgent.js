(function () {
  class GoFishVariationHeuristicAgent {
    getCurrentHand(state) {
      const current = state && state.common ? state.common.current_player : 0;
      const player = state && state.players ? state.players[current] : null;
      if (!player) {
        return [];
      }
      if (player.private && Array.isArray(player.private.hand)) {
        return player.private.hand;
      }
      if (player.facedown_cards && Array.isArray(player.facedown_cards.hand)) {
        return player.facedown_cards.hand;
      }
      return [];
    }

    // policy_metric_fixed.json[3], selected global idx=11
    scoreModelMetric(state, action) {
      const countNeededForBook = (hand, rank) => {
        let count = 0;
        for (let i = 0; i < hand.length; i += 1) {
          if (hand[i].rank === rank) {
            count += 1;
          }
        }
        return 4 - count;
      };

      const evaluateProximityToBooks = (playerHand) => {
        const rankCounts = {};
        for (let i = 0; i < playerHand.length; i += 1) {
          const rank = playerHand[i].rank;
          rankCounts[rank] = (rankCounts[rank] || 0) + 1;
        }
        return rankCounts;
      };

      const assessTurnSuccessProbability = (candidateAction, history, playerId) => {
        const requestedRank = candidateAction.args.rank;
        const targetPlayer = candidateAction.args.target_player;
        for (let i = history.length - 1; i >= 0; i -= 1) {
          const entry = history[i];
          if (entry.requester === targetPlayer && entry.rank === requestedRank) {
            return 0.6;
          }
          if (
            entry.requester === playerId &&
            entry.target === targetPlayer &&
            entry.rank === requestedRank &&
            entry.result === "fail"
          ) {
            return 0.2;
          }
        }
        return 0.4;
      };

      const adjustForKnownBooks = (playerBooks, knownBooks, playersCount) => {
        let knownTotal = 0;
        Object.keys(knownBooks || {}).forEach(function (pid) {
          const books = knownBooks[pid];
          knownTotal += Array.isArray(books) ? books.length : 0;
        });
        const maxPossibleBooks = 13;
        const remainingBooks = maxPossibleBooks - knownTotal;
        return playerBooks.length / playersCount + remainingBooks / maxPossibleBooks;
      };

      const common = state.common || {};
      const players = state.players || [];
      const faceup = common.faceup_cards || {};
      const recentHistory = faceup.turn_actions || [];
      const currentPlayer = common.current_player || 0;
      const playerHand = this.getCurrentHand(state);
      const playerBooks =
        players[currentPlayer] && players[currentPlayer].public && Array.isArray(players[currentPlayer].public.revealed_books)
          ? players[currentPlayer].public.revealed_books
          : [];
      const knownBooks = faceup.books_collected || {};
      const rankCounts = evaluateProximityToBooks(playerHand);
      const requestedRank = action.args.rank;
      const cardsNeeded = countNeededForBook(playerHand, requestedRank);
      const bookPotential = Object.prototype.hasOwnProperty.call(rankCounts, requestedRank)
        ? 1.0 - cardsNeeded / 4.0
        : 0.0;
      const actionSuccessProb = assessTurnSuccessProbability(action, recentHistory, currentPlayer);
      const baseProbability = bookPotential * actionSuccessProb;
      const competitivenessAdjustment = adjustForKnownBooks(playerBooks, knownBooks, common.num_players || 1);
      const resultScore = 0.6 * baseProbability + 0.4 * competitivenessAdjustment;
      return Math.max(0, Math.min(1, resultScore));
    }

    // policy_strategy_fixed.json[0], selected global idx=4
    scoreModelStrategy(state, action) {
      const calculateProbableRanks = (playerId, recentHistory) => {
        const requestCounts = {};
        for (let i = 0; i < recentHistory.length; i += 1) {
          const entry = recentHistory[i];
          if (entry.requester !== playerId) {
            continue;
          }
          const rank = entry.rank;
          if (!requestCounts[rank]) {
            requestCounts[rank] = [0, 0];
          }
          requestCounts[rank][0] += 1;
          if (entry.result === "success" && entry.count > 0) {
            requestCounts[rank][1] += 1;
          }
        }

        const rankConfidence = {};
        Object.keys(requestCounts).forEach(function (rank) {
          const counts = requestCounts[rank];
          const totalRequests = counts[0];
          const successes = counts[1];
          rankConfidence[rank] = totalRequests > 0 ? successes / totalRequests : 0;
        });
        return rankConfidence;
      };

      const currentPlayer = state.common.current_player || 0;
      const recentHistory = (state.common.faceup_cards && state.common.faceup_cards.turn_actions) || [];
      const rankConfidence = calculateProbableRanks(currentPlayer, recentHistory);
      const actionValue = rankConfidence[action.args.rank] || 0;
      const stockCards = state.common.facedown_cards ? state.common.facedown_cards.stock : [];
      const stockSize = Array.isArray(stockCards)
        ? stockCards.length
        : state.common.facedown_cards && Number.isFinite(state.common.facedown_cards.stock_size)
          ? state.common.facedown_cards.stock_size
          : 0;
      const booksCollected =
        state.players[currentPlayer] &&
        state.players[currentPlayer].public &&
        Array.isArray(state.players[currentPlayer].public.revealed_books)
          ? state.players[currentPlayer].public.revealed_books.length
          : 0;
      const totalBooksPossible = 13;
      const stockFactor = 1 - stockSize / 52;
      const bookFilledFactor = booksCollected / totalBooksPossible;
      const resultScore = 0.4 * actionValue + 0.3 * stockFactor + 0.3 * bookFilledFactor;
      return Math.max(0, Math.min(1, resultScore));
    }

    // policy_reflect_fixed.json[1], selected global idx=1
    scoreModelReflect(state) {
      const calculateHandStrength = (myHand) => {
        const rankCounts = {};
        for (let i = 0; i < myHand.length; i += 1) {
          const rank = myHand[i].rank;
          rankCounts[rank] = (rankCounts[rank] || 0) + 1;
        }
        let booksReady = 0;
        let booksClose = 0;
        let partialSets = 0;
        Object.keys(rankCounts).forEach(function (rank) {
          const count = rankCounts[rank];
          if (count === 4) {
            booksReady += 1;
          } else if (count === 3) {
            booksClose += 1;
          } else if (count === 2) {
            partialSets += 1;
          }
        });
        return { booksReady: booksReady, booksClose: booksClose, partialSets: partialSets };
      };

      const misdirectionOpportunity = () => {
        const actionCounts = {};
        const turnActions = (state.common.faceup_cards && state.common.faceup_cards.turn_actions) || [];
        const recentActions = turnActions.slice(Math.max(0, turnActions.length - 5));
        for (let i = 0; i < recentActions.length; i += 1) {
          const recent = recentActions[i];
          if (recent.result !== "fail") {
            continue;
          }
          const key = String(recent.target) + "|" + String(recent.rank);
          actionCounts[key] = (actionCounts[key] || 0) + 1;
        }
        let maxMisdirectCount = 0;
        Object.keys(actionCounts).forEach(function (key) {
          maxMisdirectCount = Math.max(maxMisdirectCount, actionCounts[key]);
        });
        return Math.tanh(maxMisdirectCount);
      };

      const gameProgress = () => {
        const booksCollected = (state.common.faceup_cards && state.common.faceup_cards.books_collected) || {};
        let totalBooks = 0;
        Object.keys(booksCollected).forEach(function (pid) {
          const books = booksCollected[pid];
          totalBooks += Array.isArray(books) ? books.length : 0;
        });
        return totalBooks / 13;
      };

      const myHand = this.getCurrentHand(state);
      const numPlayers = state.common.num_players || 1;
      const strength = calculateHandStrength(myHand);
      const misdirectionFactor = misdirectionOpportunity();
      const progressionFactor = gameProgress();
      const resultScore =
        0.4 * (strength.booksReady / numPlayers) +
        0.3 * (strength.booksClose / numPlayers) +
        0.1 * (strength.partialSets / numPlayers) +
        0.1 * misdirectionFactor +
        0.1 * progressionFactor;
      return Math.max(0, Math.min(1, resultScore));
    }

    score(state, action) {
      if (!state || !action || !action.args) {
        return 0;
      }
      const s1 = this.scoreModelMetric(state, action);
      const s2 = this.scoreModelStrategy(state, action);
      const s3 = this.scoreModelReflect(state);
      return (s1 + s2 + s3) / 3;
    }

    selectActionId(state, legalActions) {
      if (!Array.isArray(legalActions) || legalActions.length === 0) {
        return null;
      }

      let bestScore = -Infinity;
      let bestIndices = [];
      for (let i = 0; i < legalActions.length; i += 1) {
        const actionScore = this.score(state, legalActions[i]);
        if (actionScore > bestScore) {
          bestScore = actionScore;
          bestIndices = [i];
        } else if (actionScore === bestScore) {
          bestIndices.push(i);
        }
      }

      if (bestIndices.length === 1) {
        return bestIndices[0];
      }
      return bestIndices[Math.floor(Math.random() * bestIndices.length)];
    }
  }

  window.GoFishVariationHeuristicAgent = GoFishVariationHeuristicAgent;
})();
