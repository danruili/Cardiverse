(function () {
  function deepClone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  class MessageLog {
    constructor() {
      this.entries = [];
    }

    reset() {
      this.entries = [];
    }

    info(msg) {
      this.entries.push({ type: "info", msg: String(msg) });
    }

    getHistory() {
      return this.entries.slice();
    }
  }

  class BaseCardGameEngine {
    constructor(gameImpl, config = {}) {
      this.game = gameImpl;
      this.config = config;
      this.logger = new MessageLog();
      this.state = null;
      this.lastCardMovements = [];
      this.viewerPlayer = Number.isInteger(config.viewerPlayer) ? config.viewerPlayer : null;
    }

    reset() {
      this.logger.reset();
      this.state = this.game.initState(this.config, this.logger);
      this.lastCardMovements = [];
      return this._createDisplay();
    }

    step(actionOrId) {
      if (!this.state || this.state.common.is_over) {
        return this._createDisplay();
      }

      const previousState = deepClone(this.state);
      const legalActions = this.game.getLegalActions(this.state);
      const action = this._resolveAction(actionOrId, legalActions);
      if (!action) {
        this.logger.info("Invalid action ignored.");
        this.lastCardMovements = [];
        return this._createDisplay();
      }

      this.state = this.game.applyAction(this.state, action, this.logger);
      this.lastCardMovements = this._calculateCardMovements(previousState, this.state);

      if (this.state.common.is_over && typeof this.game.getPayoffs === "function") {
        const payoffs = this.game.getPayoffs(this.state, this.logger);
        this.state.payoffs = payoffs;
      }

      return this._createDisplay();
    }

    getState() {
      return this.state;
    }

    getCurrentPlayer() {
      return this.state ? this.state.common.current_player : null;
    }

    getLegalActions() {
      if (!this.state) {
        return [];
      }
      return this.game.getLegalActions(this.state);
    }

    getGameConfig() {
      if (this.game && typeof this.game.getConfig === "function") {
        return this.game.getConfig();
      }
      return {};
    }

    setViewerPlayer(playerIndex) {
      this.viewerPlayer = Number.isInteger(playerIndex) ? playerIndex : null;
    }

    _resolveViewerPlayerIndex(totalPlayers, fallbackIndex) {
      const resolvedTotal = Number(totalPlayers);
      const fallback = Number.isInteger(fallbackIndex) ? fallbackIndex : 0;
      if (Number.isInteger(this.viewerPlayer) && this.viewerPlayer >= 0 && this.viewerPlayer < resolvedTotal) {
        return this.viewerPlayer;
      }
      return fallback;
    }

    _resolveAction(actionOrId, legalActions) {
      if (typeof actionOrId === "object" && actionOrId !== null && actionOrId.action) {
        return actionOrId;
      }
      const id = Number(actionOrId);
      if (!Number.isInteger(id)) {
        return null;
      }
      return legalActions[id] || null;
    }

    _cardSignature(card) {
      if (!card || typeof card !== "object") {
        return null;
      }
      if (typeof card.rank === "undefined" || typeof card.suit === "undefined") {
        return null;
      }
      return String(card.rank) + "|" + String(card.suit);
    }

    _collectCardLocations(node, basePath, positionsBySig) {
      if (Array.isArray(node)) {
        node.forEach((item, idx) => {
          const itemPath = basePath + "[" + idx + "]";
          const signature = this._cardSignature(item);
          if (signature) {
            if (!positionsBySig[signature]) {
              positionsBySig[signature] = [];
            }
            positionsBySig[signature].push(itemPath);
            return;
          }
          this._collectCardLocations(item, itemPath, positionsBySig);
        });
        return;
      }
      if (!node || typeof node !== "object") {
        return;
      }
      Object.keys(node).forEach((key) => {
        const value = node[key];
        if (!value || typeof value !== "object") {
          return;
        }
        this._collectCardLocations(value, basePath ? basePath + "." + key : key, positionsBySig);
      });
    }

    _calculateCardMovements(previousState, nextState) {
      if (!previousState || !nextState) {
        return [];
      }

      const previousPositions = {};
      const nextPositions = {};
      this._collectCardLocations(previousState, "", previousPositions);
      this._collectCardLocations(nextState, "", nextPositions);

      const signatures = new Set(Object.keys(previousPositions).concat(Object.keys(nextPositions)));
      const movements = [];

      signatures.forEach((signature) => {
        const from = (previousPositions[signature] || []).slice().sort();
        const to = (nextPositions[signature] || []).slice().sort();
        const count = Math.max(from.length, to.length);
        for (let i = 0; i < count; i += 1) {
          const sourcePath = from[i] || null;
          const targetPath = to[i] || null;
          if (sourcePath !== targetPath) {
            movements.push({
              card: signature,
              from: sourcePath,
              to: targetPath,
            });
          }
        }
      });

      return movements;
    }

    _createObservation() {
      const observation = deepClone(this.state);
      const currentPlayer = observation.common.current_player;
      const viewerPlayer = this._resolveViewerPlayerIndex(
        observation.common && observation.common.num_players,
        currentPlayer
      );

      if (Array.isArray(observation.players)) {
        observation.players.forEach(function (player, idx) {
          const isViewer = idx === viewerPlayer;
          const isCurrentPlayer = idx === currentPlayer;
          if (!isViewer) {
            if (player.private) {
              delete player.private;
            }
            if (player.facedown_cards && !observation.common.is_over) {
              const facedownSizes = {};
              Object.keys(player.facedown_cards).forEach(function (key) {
                const value = player.facedown_cards[key];
                facedownSizes[key + "_size"] = Array.isArray(value) ? value.length : value;
              });
              player.facedown_cards = facedownSizes;
            }
          }
          if (observation.common.is_over) {
            player.public.final_showdown = true;
          }
          player.public.current_player = isCurrentPlayer;
          player.public.viewer_player = isViewer;
        });
      }

      if (observation.common && observation.common.facedown_cards) {
        const commonFacedown = {};
        Object.keys(observation.common.facedown_cards).forEach(function (key) {
          const value = observation.common.facedown_cards[key];
          commonFacedown[key + "_size"] = Array.isArray(value) ? value.length : value;
        });
        observation.common.facedown_cards = commonFacedown;
      }

      return observation;
    }

    _createDisplay() {
      if (!this.state) {
        return null;
      }
      const legalActions = this.game.getLegalActions(this.state).map(function (action, id) {
        return Object.assign({ id: id }, action);
      });
      const display = this._createObservation();
      display.info = { game: this.game.name };
      display["legal-actions"] = legalActions;
      display.msg = this.logger.getHistory();
      display.card_movements = this.lastCardMovements.map(function (movement) {
        return Object.assign({}, movement);
      });

      if (this.state.common.is_over && Array.isArray(this.state.payoffs)) {
        display.payoffs = this.state.payoffs.slice();
        const maxPayoff = Math.max.apply(null, display.payoffs);
        const winnerIndices = [];
        display.payoffs.forEach(function (payoff, idx) {
          if (payoff === maxPayoff) {
            winnerIndices.push(idx);
          }
        });
        if (winnerIndices.length > 0) {
          display.common.winner = winnerIndices[0];
        }
        display.players.forEach(function (player, idx) {
          player.public.payoff = display.payoffs[idx];
          player.public.is_winner = display.payoffs[idx] === maxPayoff;
        });
      }

      return display;
    }
  }

  window.BaseCardGameEngine = BaseCardGameEngine;
})();
