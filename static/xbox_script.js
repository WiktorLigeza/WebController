document.addEventListener('DOMContentLoaded', function() {
    var socket = io();
    var leftStickDisplay = document.getElementById('left-stick');
    var rightStickDisplay = document.getElementById('right-stick');
    var rtValueDisplay = document.getElementById('rt-value');
    const fromLogsToggle = document.getElementById('fromLogsToggle');

    function updateControllerDisplay(leftX, leftY, rightX, rightY, rt) {
        leftStickDisplay.textContent = leftX.toFixed(2) + ', ' + leftY.toFixed(2);
        rightStickDisplay.textContent = rightX.toFixed(2) + ', ' + rightY.toFixed(2);
        rtValueDisplay.textContent = rt.toFixed(2);
    }

    function emitControllerData(leftX, leftY, rightX, rightY, rt) {
        socket.emit('xbox_input', {
            leftX: leftX,
            leftY: leftY,
            rightX: rightX,
            rightY: rightY,
            rt: rt
        });
    }

    function gameLoop() {
        var gamepads = navigator.getGamepads ? navigator.getGamepads() : (navigator.webkitGetGamepads ? navigator.webkitGetGamepads : []);
        if (!gamepads) {
            return;
        }

        var gamepad = null;
        for (var i = 0; i < gamepads.length; i++) {
            if (gamepads[i]) {
                gamepad = gamepads[i];
                break;
            }
        }

        if (gamepad) {
            var leftX = gamepad.axes[0];   // Left stick X axis
            var leftY = -gamepad.axes[1];  // Left stick Y axis (inverted for consistency)
            var rightX = gamepad.axes[2];  // Right stick X axis
            var rightY = gamepad.axes[3];  // Right stick Y axis
            var rt = gamepad.buttons[7].value; // Right Trigger

            updateControllerDisplay(leftX, leftY, rightX, rightY, rt);
            emitControllerData(leftX, leftY, rightX, rightY, rt);
        }
        requestAnimationFrame(gameLoop);
    }

    fromLogsToggle.addEventListener('change', function() {
        const value = this.checked;
        fetch('/update_from_logs/' + value)
            .then(response => {
                if (!response.ok) {
                    console.error('Failed to update from_logs');
                }
            });
    });

    requestAnimationFrame(gameLoop);
});
