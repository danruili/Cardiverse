(function () {
  class ScreenManager {
    constructor() {
      this.startMenuScreen = document.getElementById("start-menu-screen");
      this.settingsScreen = document.getElementById("settings-screen");
      this.instructionsScreen = document.getElementById("instructions-screen");
      this.gameScreen = document.getElementById("game-screen");
      this.gameOverScreen = document.getElementById("game-over-screen");
      this.gameControls = document.getElementById("game-controls");
      this.hud = document.getElementById("hud");
    }

    show(screen) {
      this.startMenuScreen.classList.remove("active");
      this.settingsScreen.classList.remove("active");
      this.instructionsScreen.classList.remove("active");
      this.gameScreen.classList.remove("active");
      this.gameOverScreen.classList.remove("active");
      screen.classList.add("active");

      const inGame = screen.id === "game-screen";
      this.hud.style.display = inGame ? "block" : "none";
      this.gameControls.style.display = inGame ? "flex" : "none";
    }
  }

  class AppController {
    constructor() {
      this.ui = new ScreenManager();
      this.games = [];
      this.activeGame = null;
      this.EngineClass = null;
      this.HeuristicAgentClass = null;
      this.engine = null;
      this.numPlayers = 0;
      this.playerCategories = [];
      this.humanPlayerIndex = -1;
      this.heuristicAgent = null;
      this.gameConfig = {
        recommendedNumPlayers: 2,
        numPlayersRange: [2],
      };
      this.done = false;
      this.isPaused = false;
      this.lastFrameTime = 0;
      this.updateInterval = 1000 / 60;
      this.animationFrameId = null;
      this.controlsCollapsed = true;
      this.returnToGameAfterInstructions = false;
      this.startGameAfterInstructions = false;
      this.isTransitioning = false;
      this.gameBubbles = [];
    }

    init() {
      this.initGameRegistry();
      this.initGameSelector();
      this.initGameBubbles();
      this.updateGameLabels();
      this.updateInstructionsContent();
      this.initGameConfig();
      this.assignButtons();
      this.initPlayerCategorySelectors();
      this.updateInstructionsBackButtonLabel();
      setActionSelectedHandler((actionId) => {
        this.handleActionSelected(actionId).catch(function (error) {
          console.error(error);
        });
      });
      this.showMainMenu();
    }

    initGameRegistry() {
      const registry = [];
      if (window.BoatHouseRumEngine) {
        registry.push({
          id: "boat-house-rum",
          title: "Boat House Rum",
          engineClass: window.BoatHouseRumEngine,
          heuristicClass: window.BoatHouseRumHeuristicAgent || null,
        });
      }
      if (window.GoFishVariationEngine) {
        registry.push({
          id: "go-fish-misdirection",
          title: "Go Fish: Misdirection",
          engineClass: window.GoFishVariationEngine,
          heuristicClass: window.GoFishVariationHeuristicAgent || null,
        });
      }
      if (window.CrazyEightsEngine) {
        registry.push({
          id: "crazy-eights",
          title: "Crazy Eights",
          engineClass: window.CrazyEightsEngine,
          heuristicClass: window.CrazyEightsHeuristicAgent || null,
        });
      }

      if (registry.length === 0 && window.GameEngineClass) {
        registry.push({
          id: "default-game",
          title: "Card Game",
          engineClass: window.GameEngineClass,
          heuristicClass: window.GameHeuristicAgentClass || null,
        });
      }

      this.games = registry;
      this.setActiveGameById(registry.length > 0 ? registry[0].id : null);
    }

    setActiveGameById(gameId) {
      const fallbackGame = this.games.length > 0 ? this.games[0] : null;
      const targetGame = this.games.find(function (game) {
        return game.id === gameId;
      }) || fallbackGame;

      this.activeGame = targetGame;
      this.EngineClass = targetGame ? targetGame.engineClass : null;
      this.HeuristicAgentClass = targetGame ? targetGame.heuristicClass : null;
      this.engine = null;
      this.heuristicAgent = null;
    }

    initGameSelector() {
      const selector = document.getElementById("game-selector");
      if (!selector) {
        return;
      }
      selector.innerHTML = "";
      this.games.forEach((game) => {
        const option = document.createElement("option");
        option.value = game.id;
        option.textContent = game.title;
        selector.appendChild(option);
      });
      if (this.activeGame) {
        selector.value = this.activeGame.id;
      }
      selector.addEventListener("change", () => {
        this.selectGame(selector.value);
      });
    }

    selectGame(gameId) {
      this.setActiveGameById(gameId);
      this.initGameConfig();
      this.initPlayerCategorySelectors();
      this.updateGameLabels();
      this.updateInstructionsContent();
      this.updateGameBubbleState();
    }

    initGameBubbles() {
      this.gameBubbles = Array.from(document.querySelectorAll(".game-bubble"));
      if (this.gameBubbles.length === 0) {
        return;
      }
      const runAsync = (handler) => {
        return () => {
          handler().catch(function (error) {
            console.error(error);
          });
        };
      };

      this.gameBubbles.forEach((bubble) => {
        bubble.addEventListener("click", runAsync(async () => {
          const gameId = bubble.getAttribute("data-game-id");
          const exists = this.games.some(function (game) {
            return game.id === gameId;
          });
          if (!exists) {
            return;
          }
          const selector = document.getElementById("game-selector");
          if (selector) {
            selector.value = gameId;
          }
          this.selectGame(gameId);
          this.showInstructionsForSelectedGame();
        }));
      });
    }

    updateGameBubbleState() {
      if (!Array.isArray(this.gameBubbles) || this.gameBubbles.length === 0) {
        return;
      }
      const activeId = this.activeGame ? this.activeGame.id : null;
      this.gameBubbles.forEach((bubble) => {
        const isActive = bubble.getAttribute("data-game-id") === activeId;
        bubble.classList.toggle("is-active", isActive);
        bubble.setAttribute("aria-pressed", isActive ? "true" : "false");
      });
    }

    updateGameLabels() {
      const title = this.activeGame ? this.activeGame.title : "Card Game";
      const gameTitleWatermark = document.getElementById("game-title-watermark");
      if (gameTitleWatermark) {
        gameTitleWatermark.textContent = title;
      }
    }

    syncGameControlsFoldout() {
      const gameControls = document.getElementById("game-controls");
      const toggleButton = document.getElementById("game-controls-toggle");
      if (!gameControls || !toggleButton) {
        return;
      }
      gameControls.classList.toggle("collapsed", this.controlsCollapsed);
      toggleButton.setAttribute("aria-expanded", this.controlsCollapsed ? "false" : "true");
      toggleButton.textContent = this.controlsCollapsed ? "Menu" : "Close";
    }

    toggleGameControlsFoldout() {
      this.controlsCollapsed = !this.controlsCollapsed;
      this.syncGameControlsFoldout();
    }

    updateInstructionsContent() {
      const panels = document.querySelectorAll("[data-instructions-game]");
      if (!panels || panels.length === 0) {
        return;
      }
      const activeId = this.activeGame ? this.activeGame.id : null;
      panels.forEach((panel) => {
        panel.style.display = panel.getAttribute("data-instructions-game") === activeId ? "block" : "none";
      });
    }

    initGameConfig() {
      if (!this.EngineClass) {
        this.gameConfig = {
          recommendedNumPlayers: 2,
          numPlayersRange: [2],
        };
        this.numPlayers = 2;
        this.playerCategories = this.buildDefaultPlayerCategories(this.numPlayers);
        this.humanPlayerIndex = this.resolveHumanPlayerIndex(this.playerCategories);
        return;
      }
      const probeEngine = new this.EngineClass();
      const config = probeEngine.getGameConfig ? probeEngine.getGameConfig() : {};
      const recommended = Number(config.recommendedNumPlayers);
      const range = Array.isArray(config.numPlayersRange) && config.numPlayersRange.length > 0
        ? config.numPlayersRange.slice()
        : [Number.isInteger(recommended) ? recommended : 2];

      this.gameConfig = {
        recommendedNumPlayers: Number.isInteger(recommended) ? recommended : range[0],
        numPlayersRange: range,
      };
      this.numPlayers = this.gameConfig.recommendedNumPlayers;
      this.playerCategories = this.buildDefaultPlayerCategories(this.numPlayers);
      this.humanPlayerIndex = this.resolveHumanPlayerIndex(this.playerCategories);
    }

    createEngine() {
      if (!this.EngineClass) {
        this.engine = null;
        return;
      }
      this.engine = new this.EngineClass({
        numPlayers: this.numPlayers,
        viewerPlayer: this.humanPlayerIndex,
      });
    }

    buildDefaultPlayerCategories(numPlayers) {
      const total = Number.isInteger(numPlayers) && numPlayers > 0 ? numPlayers : 2;
      const categories = new Array(total).fill("random");
      const heuristicIdx = total - 1;
      const humanIdx = Math.max(0, total - 2);
      categories[humanIdx] = "human";
      if (heuristicIdx !== humanIdx) {
        categories[heuristicIdx] = "heuristic";
      }
      return categories;
    }

    resolveHumanPlayerIndex(categories) {
      if (!Array.isArray(categories) || categories.length === 0) {
        return 0;
      }
      const idx = categories.findIndex(function (category) {
        return category === "human";
      });
      return idx >= 0 ? idx : Math.max(0, categories.length - 2);
    }

    normalizePlayerCategories(categories, preferredHumanIndex) {
      const total = Number.isInteger(this.numPlayers) && this.numPlayers > 0 ? this.numPlayers : 2;
      const normalized = new Array(total).fill("random");
      for (let i = 0; i < total; i += 1) {
        const value = Array.isArray(categories) ? categories[i] : null;
        normalized[i] = value === "human" || value === "heuristic" || value === "random"
          ? value
          : "random";
      }

      const humanIndices = [];
      for (let i = 0; i < total; i += 1) {
        if (normalized[i] === "human") {
          humanIndices.push(i);
        }
      }

      const fallbackHumanIndex = Math.max(0, total - 2);
      let keepHumanIndex = -1;
      if (
        Number.isInteger(preferredHumanIndex)
        && preferredHumanIndex >= 0
        && preferredHumanIndex < total
        && normalized[preferredHumanIndex] === "human"
      ) {
        keepHumanIndex = preferredHumanIndex;
      } else if (humanIndices.length > 0) {
        keepHumanIndex = humanIndices[0];
      } else {
        keepHumanIndex = fallbackHumanIndex;
      }

      for (let i = 0; i < total; i += 1) {
        if (i !== keepHumanIndex && normalized[i] === "human") {
          normalized[i] = "random";
        }
      }
      normalized[keepHumanIndex] = "human";
      return normalized;
    }

    syncPlayerCategorySelectors() {
      const selectors = document.querySelectorAll("#player-category-settings select[data-player-index]");
      if (!selectors || selectors.length === 0) {
        return;
      }
      selectors.forEach((selector) => {
        const idx = Number(selector.getAttribute("data-player-index"));
        if (!Number.isInteger(idx) || idx < 0 || idx >= this.playerCategories.length) {
          return;
        }
        selector.value = this.playerCategories[idx] || "random";
      });
    }

    handlePlayerCategoryChanged(playerIndex, selectedValue) {
      const categories = this.playerCategories.slice();
      if (playerIndex >= 0 && playerIndex < categories.length) {
        categories[playerIndex] = selectedValue;
      }
      this.playerCategories = this.normalizePlayerCategories(categories, playerIndex);
      this.humanPlayerIndex = this.resolveHumanPlayerIndex(this.playerCategories);
      if (this.engine) {
        this.engine.setViewerPlayer(this.humanPlayerIndex);
      }
      this.syncPlayerCategorySelectors();
    }

    initPlayerCategorySelectors() {
      const container = document.getElementById("player-category-settings");
      if (!container) {
        return;
      }
      this.playerCategories = this.normalizePlayerCategories(this.playerCategories);
      this.humanPlayerIndex = this.resolveHumanPlayerIndex(this.playerCategories);
      container.innerHTML = "";
      for (let i = 0; i < this.numPlayers; i += 1) {
        const row = document.createElement("div");
        row.className = "player-seat-selector";

        const label = document.createElement("label");
        const selectId = "player-category-" + i;
        label.setAttribute("for", selectId);
        label.textContent = "Player " + (i + 1);

        const selector = document.createElement("select");
        selector.id = selectId;
        selector.setAttribute("data-player-index", String(i));

        [
          { value: "human", label: "Human" },
          { value: "heuristic", label: "Heuristic" },
          { value: "random", label: "Random" },
        ].forEach(function (item) {
          const option = document.createElement("option");
          option.value = item.value;
          option.textContent = item.label;
          selector.appendChild(option);
        });

        selector.value = this.playerCategories[i] || "random";
        selector.addEventListener("change", () => {
          this.handlePlayerCategoryChanged(i, selector.value);
        });
        row.appendChild(label);
        row.appendChild(selector);
        container.appendChild(row);
      }
    }

    readPlayerCategorySelectors() {
      const selectors = document.querySelectorAll("#player-category-settings select[data-player-index]");
      if (!selectors || selectors.length === 0) {
        return this.playerCategories.slice();
      }
      const categories = new Array(this.numPlayers).fill("random");
      selectors.forEach(function (selector) {
        const idx = Number(selector.getAttribute("data-player-index"));
        if (!Number.isInteger(idx) || idx < 0 || idx >= categories.length) {
          return;
        }
        const value = selector.value;
        categories[idx] = value === "human" || value === "heuristic" || value === "random"
          ? value
          : "random";
      });
      this.playerCategories = this.normalizePlayerCategories(categories);
      this.humanPlayerIndex = this.resolveHumanPlayerIndex(this.playerCategories);
      if (this.engine) {
        this.engine.setViewerPlayer(this.humanPlayerIndex);
      }
      this.syncPlayerCategorySelectors();
      return this.playerCategories.slice();
    }

    getPlayerCategory(playerIndex) {
      if (!Number.isInteger(playerIndex) || playerIndex < 0 || playerIndex >= this.playerCategories.length) {
        return "random";
      }
      return this.playerCategories[playerIndex] || "random";
    }

    getPlayerCategoryLabel(playerIndex) {
      const category = this.getPlayerCategory(playerIndex);
      if (category === "human") {
        return "Human";
      }
      if (category === "heuristic") {
        return "Heuristics";
      }
      return "Random";
    }

    async startGame() {
      if (this.isTransitioning) {
        return;
      }
      if (!this.EngineClass) {
        return;
      }
      this.isTransitioning = true;
      try {
        this.isPaused = false;
        this.readPlayerCategorySelectors();
        this.heuristicAgent = this.HeuristicAgentClass ? new this.HeuristicAgentClass() : null;
        this.ui.show(this.ui.gameScreen);
        this.createEngine();
        const playData = this.engine.reset();
        if (playData && playData.common && Number.isInteger(playData.common.num_players)) {
          this.numPlayers = playData.common.num_players;
          if (this.playerCategories.length !== this.numPlayers) {
            this.playerCategories = this.buildDefaultPlayerCategories(this.numPlayers);
            this.humanPlayerIndex = this.resolveHumanPlayerIndex(this.playerCategories);
            this.engine.setViewerPlayer(this.humanPlayerIndex);
            this.initPlayerCategorySelectors();
          }
        }
        await this.render(playData);
        await this.playRandomBotsUntilHumanOrGameOver();

        const state = this.engine ? this.engine.getState() : null;
        if (state && state.common && !state.common.is_over) {
          this.startLoop();
        } else {
          this.stopLoop();
        }
      } finally {
        this.isTransitioning = false;
      }
    }

    async resetGame() {
      if (this.isTransitioning) {
        return;
      }
      this.isTransitioning = true;
      try {
        if (!this.engine) {
          this.createEngine();
        }
        this.readPlayerCategorySelectors();
        this.heuristicAgent = this.HeuristicAgentClass ? new this.HeuristicAgentClass() : null;
        const playData = this.engine.reset();
        await this.render(playData);
        await this.playRandomBotsUntilHumanOrGameOver();
        this.isPaused = false;

        const state = this.engine ? this.engine.getState() : null;
        if (state && state.common && !state.common.is_over) {
          this.stopLoop();
          this.startLoop();
        } else {
          this.stopLoop();
        }
      } finally {
        this.isTransitioning = false;
      }
    }

    async handleActionSelected(actionId) {
      if (!this.engine || this.isPaused || this.isTransitioning) {
        return;
      }

      const currentPlayer = this.engine.getCurrentPlayer();
      if (this.getPlayerCategory(currentPlayer) !== "human") {
        return;
      }

      this.isTransitioning = true;
      try {
        const playData = this.engine.step(actionId);
        await this.render(playData);
        if (playData && playData.common && playData.common.is_over) {
          await this.showGameOver(playData);
          return;
        }
        await this.playRandomBotsUntilHumanOrGameOver();
      } finally {
        this.isTransitioning = false;
      }
    }

    async playRandomBotsUntilHumanOrGameOver() {
      if (!this.engine) {
        return;
      }
      let latestPlayData = null;
      let safety = 300;

      while (safety > 0) {
        safety -= 1;
        if (this.isPaused) {
          break;
        }
        const state = this.engine.getState();
        if (!state || state.common.is_over) {
          break;
        }
        if (this.getPlayerCategory(state.common.current_player) === "human") {
          break;
        }
        const legalActions = this.engine.getLegalActions();
        if (!Array.isArray(legalActions) || legalActions.length === 0) {
          break;
        }
        const actionId = this.chooseBotActionId(state, legalActions);
        if (!Number.isInteger(actionId)) {
          break;
        }
        latestPlayData = this.engine.step(actionId);
        await this.render(latestPlayData);
      }

      if (latestPlayData && latestPlayData.common && latestPlayData.common.is_over) {
        await this.showGameOver(latestPlayData);
      }
    }

    chooseBotActionId(state, legalActions) {
      const currentPlayer = state && state.common ? state.common.current_player : null;
      const category = this.getPlayerCategory(currentPlayer);
      if (category === "heuristic" && this.heuristicAgent) {
        return this.heuristicAgent.selectActionId(state, legalActions);
      }
      return Math.floor(Math.random() * legalActions.length);
    }

    async showGameOver(playData) {
      let message = "Game Over";
      const payoffs = Array.isArray(playData.payoffs) ? playData.payoffs : [];
      if (payoffs.length > 0) {
        const maxPayoff = Math.max.apply(null, payoffs);
        const winners = [];
        payoffs.forEach((value, idx) => {
          if (value === maxPayoff) {
            winners.push(idx + 1);
          }
        });
        if (winners.length === 1) {
          message = "Game Over: Player " + winners[0] + " wins";
        } else if (winners.length > 1) {
          message = "Game Over: Tie - Players " + winners.join(", ");
        }
      }
      if (!Array.isArray(playData.msg)) {
        playData.msg = [];
      }
      playData.msg.push({ type: "info", msg: message });
      playData.card_movements = [];
      await this.render(playData);
      this.ui.show(this.ui.gameScreen);
      this.stopLoop();
    }

    showMainMenu() {
      this.startGameAfterInstructions = false;
      this.returnToGameAfterInstructions = false;
      this.updateInstructionsBackButtonLabel();
      this.ui.show(this.ui.startMenuScreen);
      this.pause();
      this.controlsCollapsed = true;
      this.syncGameControlsFoldout();
    }

    showSettings() {
      this.initPlayerCategorySelectors();
      this.ui.show(this.ui.settingsScreen);
    }

    showSettingsFromGame() {
      this.pause();
      this.initPlayerCategorySelectors();
      this.ui.show(this.ui.settingsScreen);
    }

    showInstructionsFromMenu() {
      this.returnToGameAfterInstructions = false;
      this.startGameAfterInstructions = false;
      this.updateInstructionsBackButtonLabel();
      this.ui.show(this.ui.instructionsScreen);
    }

    showInstructionsFromGame() {
      this.returnToGameAfterInstructions = true;
      this.startGameAfterInstructions = false;
      this.updateInstructionsBackButtonLabel();
      this.pause();
      this.ui.show(this.ui.instructionsScreen);
    }

    showInstructionsForSelectedGame() {
      this.returnToGameAfterInstructions = false;
      this.startGameAfterInstructions = true;
      this.updateInstructionsBackButtonLabel();
      this.ui.show(this.ui.instructionsScreen);
    }

    updateInstructionsBackButtonLabel() {
      const backButton = document.getElementById("instructions-back-button");
      if (!backButton) {
        return;
      }
      if (this.startGameAfterInstructions) {
        backButton.textContent = "Start Game";
        return;
      }
      if (this.engine) {
        backButton.textContent = "Back to Game";
        return;
      }
      backButton.textContent = "Back";
    }

    pause() {
      this.isPaused = true;
      this.stopLoop();
    }

    resume() {
      this.isPaused = false;
      this.startLoop();
    }

    async render(playData) {
      await refreshUI(playData);
    }

    async applySettingsAndRestart() {
      if (this.isTransitioning) {
        return;
      }
      this.startGameAfterInstructions = false;
      this.returnToGameAfterInstructions = false;
      this.updateInstructionsBackButtonLabel();
      this.readPlayerCategorySelectors();
      this.ui.show(this.ui.gameScreen);
      await this.startGame();
    }

    startLoop() {
      if (this.animationFrameId) {
        cancelAnimationFrame(this.animationFrameId);
      }
      this.animationFrameId = requestAnimationFrame(this.gameLoop.bind(this));
    }

    stopLoop() {
      if (this.animationFrameId) {
        cancelAnimationFrame(this.animationFrameId);
        this.animationFrameId = null;
      }
    }

    gameLoop(timestamp) {
      if (this.done || this.isPaused) {
        return;
      }
      const deltaTime = timestamp - this.lastFrameTime;
      if (deltaTime > this.updateInterval) {
        this.lastFrameTime = timestamp;
      }
      this.animationFrameId = requestAnimationFrame(this.gameLoop.bind(this));
    }

    assignButtons() {
      const playButton = document.getElementById("play-button");
      const settingsButton = document.getElementById("settings-button");
      const instructionsButton = document.getElementById("instructions-button");
      const playAgainButton = document.getElementById("play-again-button");
      const gameRestartButton = document.getElementById("game-restart-button");
      const gameSettingsButton = document.getElementById("game-settings-button");
      const gameInstructionsButton = document.getElementById("game-instructions-button");
      const gameMainMenuButton = document.getElementById("game-main-menu-button");
      const gameControlsToggleButton = document.getElementById("game-controls-toggle");
      const settingsApplyButton = document.getElementById("settings-apply-button");
      const instructionsBackButton = document.getElementById("instructions-back-button");
      const mainMenuButton = document.getElementById("main-menu-button");
      const runAsync = (handler) => {
        return () => {
          handler().catch(function (error) {
            console.error(error);
          });
        };
      };

      if (playButton) {
        playButton.addEventListener("click", runAsync(this.startGame.bind(this)));
      }
      if (settingsButton) {
        settingsButton.addEventListener("click", this.showSettings.bind(this));
      }
      if (instructionsButton) {
        instructionsButton.addEventListener("click", this.showInstructionsFromMenu.bind(this));
      }
      if (playAgainButton) {
        playAgainButton.addEventListener("click", runAsync(this.startGame.bind(this)));
      }
      if (mainMenuButton) {
        mainMenuButton.addEventListener("click", this.showMainMenu.bind(this));
      }
      if (gameRestartButton) {
        gameRestartButton.addEventListener("click", runAsync(this.resetGame.bind(this)));
      }
      if (gameSettingsButton) {
        gameSettingsButton.addEventListener("click", this.showSettingsFromGame.bind(this));
      }
      if (gameInstructionsButton) {
        gameInstructionsButton.addEventListener("click", this.showInstructionsFromGame.bind(this));
      }
      if (gameMainMenuButton) {
        gameMainMenuButton.addEventListener("click", this.showMainMenu.bind(this));
      }
      if (gameControlsToggleButton) {
        gameControlsToggleButton.addEventListener("click", this.toggleGameControlsFoldout.bind(this));
      }
      if (settingsApplyButton) {
        settingsApplyButton.addEventListener("click", runAsync(this.applySettingsAndRestart.bind(this)));
      }
      this.syncGameControlsFoldout();
      if (!instructionsBackButton) {
        return;
      }
      instructionsBackButton.addEventListener("click", runAsync(async () => {
        if (this.startGameAfterInstructions) {
          this.startGameAfterInstructions = false;
          this.returnToGameAfterInstructions = false;
          this.updateInstructionsBackButtonLabel();
          await this.startGame();
          return;
        }
        if (this.engine && this.returnToGameAfterInstructions) {
          this.returnToGameAfterInstructions = false;
          this.updateInstructionsBackButtonLabel();
          this.ui.show(this.ui.gameScreen);
          this.resume();
          return;
        }
        if (this.engine) {
          this.updateInstructionsBackButtonLabel();
          this.ui.show(this.ui.gameScreen);
          this.resume();
          return;
        }
        this.showMainMenu();
      }));
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    const app = new AppController();
    app.init();
    window.getPlayerCategoryLabel = function (playerIndex) {
      return app.getPlayerCategoryLabel(playerIndex);
    };
  });
})();
