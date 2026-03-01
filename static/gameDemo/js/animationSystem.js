(function () {
  const DURATION_MS = 1500;
  const EASING = "cubic-bezier(0.22, 1, 0.36, 1)";

  function snapshotRect(rect) {
    return {
      left: rect.left,
      top: rect.top,
      width: rect.width,
      height: rect.height,
    };
  }

  function centerOf(rect) {
    return {
      x: rect.left + rect.width / 2,
      y: rect.top + rect.height / 2,
    };
  }

  function stripLastIndex(path) {
    if (!path || typeof path !== "string") {
      return null;
    }
    return path.replace(/\[\d+\]$/, "");
  }

  function withSizeSuffix(path) {
    if (!path || typeof path !== "string") {
      return null;
    }
    const parts = path.split(".");
    if (parts.length === 0) {
      return null;
    }
    const last = parts[parts.length - 1];
    if (!last || last.endsWith("_size")) {
      return null;
    }
    parts[parts.length - 1] = last + "_size";
    return parts.join(".");
  }

  function candidateZonePaths(cardPath) {
    const base = stripLastIndex(cardPath);
    if (!base) {
      return [];
    }
    const sizeVariant = withSizeSuffix(base);
    if (!sizeVariant || sizeVariant === base) {
      return [base];
    }
    return [base, sizeVariant];
  }

  function isCrossZoneMovement(movement) {
    if (!movement || !movement.from || !movement.to) {
      return false;
    }
    return stripLastIndex(movement.from) !== stripLastIndex(movement.to);
  }

  function captureLayout(root) {
    const scope = root || document;
    const cards = new Map();
    const zones = new Map();

    scope.querySelectorAll(".card[data-card-path]").forEach(function (element) {
      const cardPath = element.getAttribute("data-card-path");
      if (!cardPath) {
        return;
      }
      cards.set(cardPath, {
        rect: snapshotRect(element.getBoundingClientRect()),
        signature: element.getAttribute("data-card-signature") || null,
        element: element,
        node: element.cloneNode(true),
      });
    });

    scope.querySelectorAll(".cards[data-zone-path], .card-zone[data-zone-path]").forEach(function (element) {
      const zonePath = element.getAttribute("data-zone-path");
      if (!zonePath || zones.has(zonePath)) {
        return;
      }
      zones.set(zonePath, snapshotRect(element.getBoundingClientRect()));
    });

    return { cards: cards, zones: zones };
  }

  function resolveCard(layout, cardPath, signature) {
    const candidate = layout.cards.get(cardPath);
    if (!candidate) {
      return null;
    }
    if (signature && candidate.signature && candidate.signature !== signature) {
      return null;
    }
    return candidate;
  }

  function resolveAnchor(layout, cardPath, signature) {
    if (!layout || !cardPath) {
      return null;
    }

    const directCard = resolveCard(layout, cardPath, signature);
    if (directCard) {
      return {
        rect: directCard.rect,
        card: directCard,
      };
    }

    const zonePaths = candidateZonePaths(cardPath);
    for (let i = 0; i < zonePaths.length; i += 1) {
      const zoneRect = layout.zones.get(zonePaths[i]);
      if (zoneRect) {
        return {
          rect: zoneRect,
          card: null,
        };
      }
    }
    return null;
  }

  function createFallbackGhost() {
    const ghost = document.createElement("div");
    ghost.className = "card card-flip";
    return ghost;
  }

  function animateSingleMovement(movement, beforeLayout, afterLayout) {
    const source = resolveAnchor(beforeLayout, movement.from, movement.card);
    const target = resolveAnchor(afterLayout, movement.to, movement.card);
    if (!source || !target) {
      return Promise.resolve(false);
    }

    const template = source.card ? source.card.node : (target.card ? target.card.node : createFallbackGhost());
    const ghost = template.cloneNode(true);
    ghost.classList.add("card-movement-ghost");
    ghost.style.transition = "none";

    const sourceRect = source.rect;
    const targetRect = target.rect;
    const width = (source.card && source.card.rect.width) || (target.card && target.card.rect.width) || 42;
    const height = (source.card && source.card.rect.height) || (target.card && target.card.rect.height) || 58;
    const sourceCenter = centerOf(sourceRect);
    const targetCenter = centerOf(targetRect);
    const dx = targetCenter.x - sourceCenter.x;
    const dy = targetCenter.y - sourceCenter.y;

    ghost.style.width = width + "px";
    ghost.style.height = height + "px";
    ghost.style.left = (sourceCenter.x - width / 2) + "px";
    ghost.style.top = (sourceCenter.y - height / 2) + "px";
    ghost.style.opacity = "1";

    let hiddenTarget = null;
    if (target.card && target.card.element) {
      hiddenTarget = target.card.element;
      hiddenTarget.classList.add("card-animation-hidden");
    }

    document.body.appendChild(ghost);

    return new Promise(function (resolve) {
      let finished = false;
      function finish() {
        if (finished) {
          return;
        }
        finished = true;
        if (hiddenTarget) {
          hiddenTarget.classList.remove("card-animation-hidden");
        }
        if (ghost.parentNode) {
          ghost.parentNode.removeChild(ghost);
        }
        resolve(true);
      }

      ghost.addEventListener("transitionend", finish, { once: true });
      setTimeout(finish, DURATION_MS + 140);

      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          ghost.style.transition = "transform " + DURATION_MS + "ms " + EASING;
          ghost.style.transform = "translate(" + dx + "px, " + dy + "px)";
        });
      });
    });
  }

  function animate(movements, beforeLayout) {
    if (!Array.isArray(movements) || movements.length === 0 || !beforeLayout) {
      return Promise.resolve();
    }
    const afterLayout = captureLayout(document);
    const tasks = movements
      .filter(isCrossZoneMovement)
      .map(function (movement) {
        return animateSingleMovement(movement, beforeLayout, afterLayout);
      });
    if (tasks.length === 0) {
      return Promise.resolve();
    }
    return Promise.all(tasks).then(function () {});
  }

  window.CardMovementAnimator = {
    captureLayout: captureLayout,
    animate: animate,
  };
})();
