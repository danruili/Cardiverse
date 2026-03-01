

function createPlayerAttr(key, value) {
    // Create a container div for the attribute
    const container = document.createElement('div');
    container.className = 'attr-field';
    container.setAttribute('attr-title', key);
    
    // Create a key element
    const keyElement = document.createElement('div');
    keyElement.className = 'attr-key';
    keyElement.textContent = key;
    
    // Create a value element
    const valueElement = document.createElement('div');
    valueElement.className = 'attr-value';
    valueElement.textContent = value;
    
    // Append the elements to the container
    container.appendChild(keyElement);
    container.appendChild(valueElement);
    
    return container;
}

function createPlayerCategoryBadge(playerStateIndex) {
    const badge = document.createElement('div');
    badge.className = 'player-category-badge';
    const getLabel = window.getPlayerCategoryLabel;
    const hasIndex = Number.isInteger(playerStateIndex) && playerStateIndex >= 0;
    if (typeof getLabel === 'function' && hasIndex) {
        badge.textContent = getLabel(playerStateIndex);
        return badge;
    }
    badge.textContent = 'Random';
    return badge;
}

function createCurrentPlayerAttrList(data, playerStateIndex) {
    const mainContainer = document.createElement('div');
    mainContainer.className = 'player-attr-container';

    const portrait = document.createElement('div');
    portrait.className = 'portrait-contrainer';
    if (data && data['public'] && data['public']['current_player']) {
        portrait.className += ' active';
    }
    if (data && data['public'] && data['public']['is_winner']) {
        portrait.className += ' winner-avatar';
    }
    mainContainer.appendChild(portrait);
    mainContainer.appendChild(createPlayerCategoryBadge(playerStateIndex));
    
    // Create a main container to hold all card zones
    const attrContainer = document.createElement('div');
    attrContainer.className = 'attr-container';
    mainContainer.appendChild(attrContainer);

    // Check if the input data contains card attributes
    if (data['public']) {
        const playerAttributes = data['public'];

        // Iterate over each field in the card attributes
        for (const [key, value] of Object.entries(playerAttributes)) {
            const keyName = key.replace(/_/g, ' ').replace(/(?:^|\s)\S/g, letter => letter.toUpperCase());
            const attrField = createPlayerAttr(keyName, value);
            attrContainer.appendChild(attrField);
        }
    }

    return mainContainer;
}

function createPlayerAttrList(data, public=false, index, playerStateIndex=null) {
    const mainContainer = document.createElement('div');
    mainContainer.className = 'player-attr-container';

    if (public === false){
        // console.log(index);
        const portrait = document.createElement('div');
        portrait.className = 'portrait-contrainer';
        if (data && data['public'] && data['public']['current_player']) {
            portrait.className += ' active';
        }
        if (data && data['public'] && data['public']['is_winner']) {
            portrait.className += ' winner-avatar';
        }
        // Add index number
        const indexNumber = document.createElement('div');
        indexNumber.className = 'player-index';
        indexNumber.textContent = "Player " + (index);
        
        mainContainer.appendChild(portrait);
        mainContainer.appendChild(indexNumber);
        mainContainer.appendChild(createPlayerCategoryBadge(playerStateIndex));
    }

    // Create a main container to hold all card zones
    const attrContainer = document.createElement('div');
    attrContainer.className = 'attr-container';
    mainContainer.appendChild(attrContainer);

    // Check if the input data contains attributes
    if (data['public']) {
        const playerAttributes = data['public'];

        // Iterate over each field in the card attributes
        for (const [key, value] of Object.entries(playerAttributes)) {
            const keyName = key.replace(/_/g, ' ').replace(/(?:^|\s)\S/g, letter => letter.toUpperCase());
            const attrField = createPlayerAttr(keyName, value);
            attrContainer.appendChild(attrField);
        }
    }
    if (public){
        exclude_fields = ['current_player', 'is_over', 'winner', 'facedown_cards', 'faceup_cards', 'num_players'];
        // directly iterate over the data
        for (const [key, value] of Object.entries(data)) {
            if (!exclude_fields.includes(key)){
                const keyName = key.replace(/_/g, ' ').replace(/(?:^|\s)\S/g, letter => letter.toUpperCase());
                const attrField = createPlayerAttr(keyName, value);
                attrContainer.appendChild(attrField);
            }
        }
    }

    // Append the main container to the body or another element in the DOM
    return mainContainer;
}

function createPlayerProfile(data, visualIndex, otherPlayerNum, playerNumber, playerStateIndex) {
    // Create a container div for the player profile
    const container = document.createElement('div');

    // add current player class if it is the current player
    container.className = 'player-profile';
    // if only one other player, add north-player class
    if (otherPlayerNum == 1){
        container.className = 'player-profile north-player';
    }
    // if two other players, add west-player class for the first one and east-player class for the second one
    else if (otherPlayerNum == 2){
        if (visualIndex == 0){
            container.className = 'player-profile west-player';
        }
        else if (visualIndex == 1){
            container.className = 'player-profile east-player';
        }
    }
    else if (otherPlayerNum == 3){
        if (visualIndex == 0){
            container.className = 'player-profile west-player';
        }
        else if (visualIndex == 1){
            container.className = 'player-profile north-player';
        }
        else if (visualIndex == 2){
            container.className = 'player-profile east-player';
        }
    }
    if (data && data['public'] && data['public']['is_winner']) {
        container.className += ' winner-profile';
    }
    if (data && data['public'] && data['public']['current_player']) {
        container.className += ' current-turn-player';
    }


    // Create a player attributes list
    const attrList = createPlayerAttrList(data, public=false, playerNumber, playerStateIndex);
    container.appendChild(attrList);

    // Create a card zone list
    const cardZoneList = createCardZoneList(data, "players[" + playerStateIndex + "]");
    container.appendChild(cardZoneList);

    return container;
}

function createCurrentPlayerProfile(data, playerStateIndex) {
    // Create a container div for the player profile
    const container = document.createElement('div');

    // add current player class if it is the current player
    container.className = 'player-profile-current-player';
    if (data && data['public'] && data['public']['current_player']) {
        container.className += ' current-turn-player';
    }
    if (data && data['public'] && data['public']['is_winner']) {
        container.className += ' winner-profile';
    }

    // Create a player attributes list
    const attrList = createCurrentPlayerAttrList(data, playerStateIndex);
    container.appendChild(attrList);

    // Create a card zone list
    const cardZoneList = createCardZoneList(data, "players[" + playerStateIndex + "]");
    container.appendChild(cardZoneList);

    return container;
}

function createPlayerProfileList(data) {
    // Create a main container to hold all player profiles
    const mainContainer = document.createElement('div');
    mainContainer.className = 'player-profile-container';

    // Check if the input data contains player profiles
    if (data['players']) {
        const playerProfiles = data['players'];
        const otherPlayerNum = playerProfiles.length - 1; // Exclude the current player

        const otherPlayers = playerProfiles
            .map((playerData, index) => ({ playerData, index }))
            .filter(({ playerData }) => !playerData['public']['viewer_player']);

        // Use visual index among non-current players so placement remains stable each turn
        otherPlayers.forEach(({ playerData, index }, visualIndex) => {
            const playerProfile = createPlayerProfile(playerData, visualIndex, otherPlayerNum, index + 1, index);
            mainContainer.appendChild(playerProfile);
        });
    }

    // Append the main container to the body or another element in the DOM
    return mainContainer;
}

function createCurrentPlayerProfileList(data) {
    // Create a main container to hold all player profiles
    const mainContainer = document.createElement('div');
    mainContainer.className = 'player-profile-container';

    // Check if the input data contains player profiles
    if (data['players']) {
        const playerProfiles = data['players'];

        // Iterate over each player profile and find the current player
        playerProfiles.forEach((playerData, idx) => {
            if (playerData['public']['viewer_player']) {
                const playerProfile = createCurrentPlayerProfile(playerData, idx);
                mainContainer.className =  'current-player-profile-container';
                mainContainer.appendChild(playerProfile);
            }
        });
    }

    // Append the main container to the body or another element in the DOM
    return mainContainer;
}

function createPublicProfile(data) {
    const publicData = data;

    // Create a container div for the player profile
    const container = document.createElement('div');
    container.className = 'public-profile';

    // Create a player attributes list
    const attrList = createPlayerAttrList(publicData['common'], public=true);
    container.appendChild(attrList);

    // Create a card zone list
    const cardZoneList = createCardZoneList(publicData['common'], 'common');
    container.appendChild(cardZoneList);

    return container;
}

function updateGameControls(data) {
    const gameTitleWatermark = document.getElementById('game-title-watermark');
    if (gameTitleWatermark && data && data['info'] && data['info']['game']) {
        gameTitleWatermark.textContent = data['info']['game'];
    }

    const historyPanel = document.getElementById('game-history-panel');
    const historyButton = document.getElementById('game-history-button');
    if (!historyPanel || !historyButton) {
        return;
    }

    const expanded = historyButton.getAttribute('aria-expanded') === 'true';
    const msgList = createMsgList(data);
    msgList.setExpanded(expanded);

    historyPanel.classList.toggle('open', expanded);
    historyPanel.replaceChildren(msgList);

    historyButton.disabled = !msgList.hasHistory;
    historyButton.textContent = msgList.hasHistory
        ? (expanded ? 'Hide History' : 'History')
        : 'No History';

    historyButton.onclick = () => {
        if (!msgList.hasHistory) {
            return;
        }
        const nextExpanded = historyButton.getAttribute('aria-expanded') !== 'true';
        historyButton.setAttribute('aria-expanded', nextExpanded ? 'true' : 'false');
        historyButton.textContent = nextExpanded ? 'Hide History' : 'History';
        historyPanel.classList.toggle('open', nextExpanded);
        msgList.setExpanded(nextExpanded);
    };
}

function createGameInfo(data) {
    // Create a container div for the game info
    const container = document.createElement('div');
    container.className = 'game-info';

    const gameInfo = data['info'];

    const gameTitle = document.createElement('h1');
    gameTitle.className = 'game-title';
    gameTitle.textContent = gameInfo['game'];
    container.appendChild(gameTitle);

    return container;
}
