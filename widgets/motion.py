from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPauseAnimation, QPropertyAnimation, QSequentialAnimationGroup
from PySide6.QtWidgets import QGraphicsOpacityEffect, QPushButton


class ButtonMotion(QObject):
    def __init__(self, parent):
        super().__init__(parent)
        self.animations = {}

    def install(self, root):
        for button in root.findChildren(QPushButton):
            effect = QGraphicsOpacityEffect(button)
            effect.setOpacity(0.94)
            button.setGraphicsEffect(effect)
            button.installEventFilter(self)

    def eventFilter(self, watched, event):
        if isinstance(watched, QPushButton) and watched.isEnabled():
            if event.type() == QEvent.Enter:
                self._animate(watched, 1.0)
            elif event.type() == QEvent.Leave:
                self._animate(watched, 0.94)
            elif event.type() == QEvent.MouseButtonPress:
                self._animate(watched, 0.72, 70)
            elif event.type() == QEvent.MouseButtonRelease:
                self._animate(watched, 1.0, 110)
        return False

    def _animate(self, button, target, duration=140):
        effect = button.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            return
        animation = QPropertyAnimation(effect, b"opacity", button)
        animation.setDuration(duration)
        animation.setStartValue(effect.opacity())
        animation.setEndValue(target)
        animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animations[id(button)] = animation
        animation.start()


def stagger_cards(cards, owner):
    owner._intro_animations = []
    for index, card in enumerate(cards):
        effect = QGraphicsOpacityEffect(card)
        effect.setOpacity(0.0)
        card.setGraphicsEffect(effect)
        group = QSequentialAnimationGroup(owner)
        group.addAnimation(QPauseAnimation(index * 55))
        animation = QPropertyAnimation(effect, b"opacity")
        animation.setDuration(300)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.OutCubic)
        group.addAnimation(animation)
        group.finished.connect(lambda target=card: target.setGraphicsEffect(None))
        owner._intro_animations.append(group)
        group.start()
