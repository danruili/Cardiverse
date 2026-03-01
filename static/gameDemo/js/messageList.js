function createMsgList(data) {
    const msgData = data['msg'].filter(msg => msg['type'] === 'info');

    const container = document.createElement('div');
    container.className = 'msg-list';

    const msgContainer = document.createElement('div');
    msgContainer.className = 'msg-container';
    msgContainer.style.display = 'none';

    msgData.forEach((msg, index) => {
        const msgElement = document.createElement('div');
        msgElement.className = 'msg';
        msgElement.textContent = msg['msg'];
        msgElement.setAttribute('msg-index', String(index));
        msgContainer.appendChild(msgElement);
    });

    container.setExpanded = (expanded) => {
        container.classList.toggle('open', expanded);
        msgContainer.style.display = expanded ? 'flex' : 'none';
    };

    if (msgData.length === 0) {
        const emptyMsg = document.createElement('div');
        emptyMsg.className = 'msg';
        emptyMsg.textContent = 'No history yet.';
        msgContainer.appendChild(emptyMsg);
    }

    container.hasHistory = msgData.length > 0;
    container.setExpanded(false);
    container.appendChild(msgContainer);

    return container;
}
