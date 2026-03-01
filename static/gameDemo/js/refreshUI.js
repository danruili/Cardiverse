function refreshUI(playData) {
    const animator = window.CardMovementAnimator;
    const beforeLayout = animator ? animator.captureLayout(document) : null;

    // update game info, game board, and action board
    $(".public-info-wrapper").html(createPublicProfile(playData));
    $(".player-info-wrapper").html(createPlayerProfileList(playData));
    $(".current-player-info-wrapper").html(createCurrentPlayerProfileList(playData));
    $(".action-board-wrapper").html(createActionBoard(playData));
    updateGameControls(playData);

    bindActionBoardEvents(document.querySelector(".action-board-wrapper"));

    if (!animator || !beforeLayout) {
        return Promise.resolve();
    }
    const movements = Array.isArray(playData && playData.card_movements) ? playData.card_movements : [];
    return animator.animate(movements, beforeLayout);
}
