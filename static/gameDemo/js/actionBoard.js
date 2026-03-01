let actionSelectedHandler = null;

function setActionSelectedHandler(handler) {
    actionSelectedHandler = typeof handler === 'function' ? handler : null;
}

function bindActionBoardEvents(root = document) {
    const $root = $(root);
    $root.off("click", ".lower-level-action-button");
    $root.on("click", ".lower-level-action-button", function() {
        if (!actionSelectedHandler) {
            return;
        }
        const actionId = $(this).attr("id");
        actionSelectedHandler(actionId);
    });
}

function createActionBoard(data) {
    const container = document.createElement('div');
    container.className = 'action-container';

    // Reset container
    container.innerHTML = '';

    const viewerPlayer = Array.isArray(data['players'])
        ? data['players'].find(player => player && player['public'] && player['public']['viewer_player'])
        : null;
    const isViewerTurn = viewerPlayer && viewerPlayer['public'] && viewerPlayer['public']['current_player'];

    // Hide actions while bots are taking their turns to prevent accidental clicks.
    if (viewerPlayer && !isViewerTurn) {
        return container;
    }

    if (data['legal-actions'] && !data['common']['is_over']) {
        const legalActions = data['legal-actions'];

        // Optional hint logic
        const actionHint = data['hint'] || {};

        // Group actions by action name
        const actionGroups = {};
        legalActions.forEach(action => {
            const actionName = action['action'];
            if (!actionGroups[actionName]) {
                actionGroups[actionName] = [];
            }
            actionGroups[actionName].push(action);
        });

        // Create top-level action buttons
        Object.keys(actionGroups).forEach(actionName => {
            const topButton = document.createElement('button');
            topButton.textContent = actionName;

            if (actionGroups[actionName].length == 1 && !actionGroups[actionName][0]['args']) {
                // Use lower-level button for single actions without arguments
                topButton.className = 'action-button lower-level-action-button';
                topButton.id = actionGroups[actionName][0]['id'];
            }else{
                topButton.className = 'action-button top-level-action-button';
                topButton.addEventListener('click', () => {
                    // Replace the container content with argument-level buttons
                    renderArguments(actionGroups[actionName]);
                });
            }
            container.appendChild(topButton);
        });

        // Function to render argument-level buttons
        function renderArguments(actionList) {
            container.innerHTML = ''; // Clear previous buttons
            actionList.forEach(action => {
                const actionElement = document.createElement('button');
                actionElement.className = 'action-button lower-level-action-button';
                
                if (actionHint['id'] === action['id']) {
                    actionElement.classList.add('action-hint');
                }

                let actionString = "";
                let card_element = null;

                if (action['args']) {
                    // find if the action contains card index key
                    const indexKeyPool = ['card_idx', 'card_index'];
                    let index_key = null;
                    for (const key of indexKeyPool) {
                        if (key in action['args']) {
                            index_key = key;
                            break;
                        }
                    }  
                    
                    // if contains card index key, then it is a card action
                    if (index_key){
                        const actor = data['players'].find(player => player['public']['viewer_player'])
                            || data['players'].find(player => player['public']['current_player']);
                        const hand = actor && actor['facedown_cards'] ? actor['facedown_cards']['hand'] : [];
                        const cardIdx = action['args'][index_key];
                        let card_dict = hand[cardIdx];
                        if (typeof card_dict !== 'undefined') {
                            card_dict = formatCardDict(card_dict);
                            card_element = createCard(card_dict);
                            actionElement.style.marginBottom = "0em";
                        }
                    }

                    // Create a string for remaining arguments
                    // Create container for arguments
                    const argListDiv = document.createElement('div');
                    argListDiv.className = 'action-arg-list';
                    
                    // Filter and process each argument
                    Object.entries(action['args'])
                        .filter(([key, _]) => key !== 'id' && key !== index_key)
                        .forEach(([key, value]) => {
                            const argDiv = document.createElement('div');
                            argDiv.className = 'action-arg';
                            
                            const keyDiv = document.createElement('div');
                            keyDiv.className = 'action-arg-key';
                            keyDiv.textContent = formatDisplayField(key);
                            
                            const valDiv = document.createElement('div');
                            valDiv.className = 'action-arg-val';
                            if (typeof value === 'object') {
                                value = JSON.stringify(value);
                            }
                            if (typeof value === 'string') {
                                valDiv.textContent = formatDisplayField(value);
                            }
                            else {
                                valDiv.textContent = value;
                            }
                            
                            argDiv.appendChild(keyDiv);
                            argDiv.appendChild(valDiv);
                            argListDiv.appendChild(argDiv);
                        });
                    
                    if (argListDiv.childNodes.length > 0) {
                        actionElement.appendChild(argListDiv);
                    }
                }
                
                // If there's no content yet, add the action name
                if (!actionElement.hasChildNodes()) {
                    actionElement.textContent = actionString;
                }
                actionElement.id = action['id'];

                // set card style if it is a card action
                if (card_element){
                    actionElement.appendChild(card_element);
                    actionElement.className += ' card-action-button';
                    container.className += ' card-action-container';
                    if (actionString.length > 0){
                        actionElement.style.padding = "0.5em";
                    }else{
                        actionElement.style.padding = "0" 
                    }
                }

                container.appendChild(actionElement);
            });

            // Add a back button to return to top-level actions
            const backButton = document.createElement('button');
            backButton.className = 'action-button back-action-button';
            backButton.textContent = '⬅ Back';
            backButton.addEventListener('click', () => {
                $(".action-board-wrapper").html(createActionBoard(data)); // Re-render top level
                setTimeout(function() {
                    bindActionBoardEvents(document.querySelector(".action-board-wrapper"));
                }, 0);
            });
            container.appendChild(backButton);
        }
    }

    return container;
}

// function that convert _ to space, capitalize the first letter
function formatDisplayField(str) {
    return str.charAt(0).toUpperCase() + str.slice(1).replace(/_/g, ' ');
}
