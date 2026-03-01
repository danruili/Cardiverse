function getSuitSymbol(suit) {
    switch (suit) {
        case 'heart':
            return '♥';
        case 'diamond':
            return '♦';
        case 'club':
            return '♣';
        case 'spade':
            return '♠';
        case 'hearts':
            return '♥';
        case 'diamonds':
            return '♦';
        case 'clubs':
            return '♣';
        case 'spades':
            return '♠';
        default:
            return '';
    }
}

function formatCardDict(card) {
    if (typeof card === 'string') {
        if (!isNaN(card)) {
            // if it is a number string, treat it as a rank
            console.log("Card is a number string: " + card);
            card = {'rank': card};
            return card;
        }
        try { 
            // try to parse the string as a json object
            card = JSON.parse(card.replace(/'/g, '"').replace(/True/g, 'true').replace(/False/g, 'false'));
            // If the card has an is_card property, delete it
            if (card && card.is_card !== undefined) {
                delete card.is_card;
            }
            if (card && card.field !== undefined) {
                delete card.field;
            }
            if (card && card.str !== undefined) {
                delete card.str;
            }
        }
        catch (e) {
            // if it fails, treat it as a field
            console.log("Failed to parse card string as JSON object: " + card);
            return {'field': card};
        } 
        return card;
    }
    else if (typeof card === 'object') {
        if (card && card.is_card !== undefined) {
            delete card.is_card;
        }
        if (card && card.field !== undefined) {
            delete card.field;
        }
        if (card && card.str !== undefined) {
            delete card.str;
        }
        return card;
    }
    else {
        console.log(card);
        throw new Error('Invalid card format');
    }
}

function getCardSignature(card) {
    if (!card || typeof card !== 'object') {
        return null;
    }
    if (!('rank' in card) || !('suit' in card)) {
        return null;
    }
    return String(card.rank) + "|" + String(card.suit);
}

function getCssLengthInEm(varName, fallbackEm) {
    const rootStyle = getComputedStyle(document.documentElement);
    const rawValue = rootStyle.getPropertyValue(varName).trim();
    if (!rawValue) {
        return fallbackEm;
    }

    const fontSizePx = parseFloat(rootStyle.fontSize) || 16;
    const probe = document.createElement('div');
    probe.style.position = 'absolute';
    probe.style.visibility = 'hidden';
    probe.style.pointerEvents = 'none';
    probe.style.width = rawValue;

    const mountTarget = document.body || document.documentElement;
    mountTarget.appendChild(probe);
    const widthPx = probe.getBoundingClientRect().width;
    mountTarget.removeChild(probe);

    if (Number.isFinite(widthPx) && widthPx > 0) {
        return widthPx / fontSizePx;
    }

    const numericValue = parseFloat(rawValue);
    if (Number.isNaN(numericValue)) {
        return fallbackEm;
    }
    if (rawValue.endsWith('px')) {
        return numericValue / fontSizePx;
    }
    if (rawValue.endsWith('em')) {
        return numericValue;
    }
    return fallbackEm;
}

function createCardZone(cards, zone_title, is_facedown=false, zone_path="") {
    // Create a card list with title
    const container = document.createElement('div');
    container.className = 'card-zone';
    container.setAttribute('card-title', zone_title);
    if (zone_path) {
        container.setAttribute("data-zone-path", zone_path);
    }
    if (is_facedown) {
        container.className += ' facedown-zone';
    }

    // Create a title
    const title = document.createElement('div');
    title.className = 'card-zone-title';
    title.textContent = zone_title;
    container.appendChild(title);

    // Create a card list
    const cardList = createCardList(cards, zone_path);
    if (zone_path) {
        cardList.setAttribute("data-zone-path", zone_path);
    }
    container.appendChild(cardList);

    return container;
}

function createCardList(cards, card_path="") {
    // Create a container div for the cards
    const container = document.createElement('div');
    container.className = 'cards';

    const cardSkip = getCssLengthInEm('--card-skip', 1.2); // gap between cards
    const cardTop = getCssLengthInEm('--card-top', 3); // verticle gap between cards
    const cardWidth = getCssLengthInEm('--card-width', 2.5); // width of each card
    const cardHeight = getCssLengthInEm('--card-height', 3.5); // height of each card
    const offset = -0; // offset for visual effect

    // width is (card-count-1) x gap + card-width
    const cardRows = Math.ceil(cards.length / 8); // 8 cards per row
    const cardCountInRow = cards.length > 8 ? 8 : cards.length;
    container.style.setProperty('width', `${(cardCountInRow-1) * cardSkip + cardWidth + offset}em`);
    container.style.setProperty('height', `${(cardRows-1) * cardTop + cardHeight}em`);
    
    // Iterate through each card and create an element
    cards.forEach((card, idx) => {
        const itemPath = card_path ? (card_path + "[" + idx + "]") : ("[" + idx + "]");
        // If card is an array, recursively create a card list
        if (Array.isArray(card)) {
            container.className = 'sub-card-zone';
            container.style.setProperty('width', `auto`);
            container.style.setProperty('height', `auto`);
            const cardList = createCardList(card, itemPath);
            container.appendChild(cardList);
        }
        else{
            // Create each card element
            const cardDiv = createCard(card, itemPath);
            const col = idx % 8;
            const row = Math.floor(idx / 8);
            cardDiv.style.setProperty('--col', col);
            cardDiv.style.setProperty('--row', row);
            cardDiv.style.setProperty('--z', idx + 1);
            container.appendChild(cardDiv);
        }
    });
    
    return container;
}

function createCard(card_source, card_path="") {
    // parse card to object if it is a json string
    const card = formatCardDict(card_source);

    const cardDiv = document.createElement('div');
    cardDiv.className = 'card';
    if (card_path) {
        cardDiv.setAttribute("data-card-path", card_path);
    }

    // if undefined
    if (!card) {
        console.log(card);
        throw new Error('Invalid card format');
    }

    // Add suit and rank as text content
    if ('rank' in card) {
        const rankElement = document.createElement('div');
        rankElement.textContent = card.rank;
        rankElement.className = 'rank';
        rankElement.style.color = card.suit === 'heart' || card.suit === 'diamond' || card.suit === 'hearts' || card.suit === 'diamonds' ? 'red' : 'black';
        cardDiv.appendChild(rankElement);
    }
    
    if ('suit' in card) {
        const suitElement = document.createElement('div');
        suitElement.className = 'suit';
        suitElement.textContent = getSuitSymbol(card.suit);
        suitElement.style.color = card.suit === 'heart' || card.suit === 'diamond' || card.suit === 'hearts' || card.suit === 'diamonds' ? 'red' : 'black';
        cardDiv.appendChild(suitElement);
    }

    if ('flip' in card && card['flip']) {
        cardDiv.className += ' card-flip';
    }

    if ('num-label' in card) {
        const centralTextElement = document.createElement('div');
        centralTextElement.className = 'num-label';
        centralTextElement.textContent = card['num-label'];
        cardDiv.appendChild(centralTextElement);
    }

    const signature = getCardSignature(card);
    if (signature) {
        cardDiv.setAttribute("data-card-signature", signature);
    }

    // if any other fields in the card, add them as text content
    for (const [key, value] of Object.entries(card)) {
        if (key !== 'rank' && key !== 'suit' && key !== 'flip' && key !== 'num-label') {
            const fieldElement = document.createElement('div');
            fieldElement.className = 'field';
            fieldElement.textContent = value;
            cardDiv.appendChild(fieldElement);
        }
    }
    return cardDiv;
}

function createCardZoneList(data, base_path="") {
    // face-down card display num
    const default_display_card_num = window.innerWidth < 768 ? 1 : 4;

    // Create a main container to hold all card zones
    const mainContainer = document.createElement('div');
    mainContainer.className = 'card-zone-container';

    if (data['faceup_cards']) {
        const cardAttributes = data['faceup_cards'];
        const hiddenFaceupZones = new Set(['turn_actions']);

        // Iterate over each field in the card attributes
        for (const [key, cards] of Object.entries(cardAttributes)) {
            if (hiddenFaceupZones.has(key)) {
                continue;
            }
            // Check if the value is an array of cards
            if (Array.isArray(cards) && cards.length > 0) {
                // Create a human-readable title based on the key
                const zoneTitle = key.replace(/_/g, ' ').replace(/(?:^|\s)\S/g, letter => letter.toUpperCase());
                const zonePath = base_path ? (base_path + ".faceup_cards." + key) : ("faceup_cards." + key);
                const cardZone = createCardZone(cards, zoneTitle, false, zonePath);
                mainContainer.appendChild(cardZone);
            }
        }
    }

    if (data['facedown_cards']) {
        const cardAttributes = data['facedown_cards'];

        if ((!('public' in data) && (data['is_over'])) // it is common info and game is over
            || (('public' in data) && (data['public']['viewer_player'] || data['public']['final_showdown'])) // it is viewer player or final showdown
        ) {
            // show faced-up since it's the current player or final showdown
            for (const [key, cards] of Object.entries(cardAttributes)) {
                if (Array.isArray(cards) && cards.length > 0) {
                    // Create a human-readable title based on the key
                    const zoneTitle = key.replace(/_/g, ' ').replace(/(?:^|\s)\S/g, letter => letter.toUpperCase());
                    const zonePath = base_path ? (base_path + ".facedown_cards." + key) : ("facedown_cards." + key);
                    const cardZone = createCardZone(cards, zoneTitle, false, zonePath);
                    mainContainer.appendChild(cardZone);
                }
            }
        }
        else
        {
            // Show facedown cards
            for (const [key, card_num] of Object.entries(cardAttributes)) {
                if (card_num <= 0) {
                    continue;
                }
                let display_card_num = card_num > default_display_card_num-1 ? default_display_card_num : card_num;
                // construct array of {'flip': true} to represent facedown cards
                // for the last card, add num-label
                const cards = Array(display_card_num-1).fill({'flip': true});
                if (card_num > default_display_card_num-1) {
                    cards.push({'flip': true, 'num-label': "+" + (card_num - (default_display_card_num - 1))});
                }
                else {
                    cards.push({'flip': true});
                }

                const zoneTitle = key.replace(/_/g, ' ').replace(/(?:^|\s)\S/g, letter => letter.toUpperCase());
                const zonePath = base_path ? (base_path + ".facedown_cards." + key) : ("facedown_cards." + key);
                const cardZone = createCardZone(cards, zoneTitle, true, zonePath);
                mainContainer.appendChild(cardZone);
            }
        }
    }

    // Append the main container to the body or another element in the DOM
    return mainContainer;
}
