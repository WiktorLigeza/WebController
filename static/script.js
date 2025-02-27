document.addEventListener('DOMContentLoaded', function() {
    var socket = io();
    var keys = document.querySelectorAll('.key');
    var pressedKeys = [];
    var intervalId;

    function updateKeysStyle() {
        keys.forEach(function(key) {
            var keyValue = key.getAttribute('data-key');
            if (pressedKeys.includes(keyValue)) {
                key.style.backgroundColor = 'lightgreen';
            } else {
                key.style.backgroundColor = ''; // Reset to default
            }
        });
    }

    function emitKeys() {
        socket.emit('keys_pressed', pressedKeys);
    }

    keys.forEach(function(key) {
        key.addEventListener('mousedown', function() {
            var keyValue = this.getAttribute('data-key');
            if (!pressedKeys.includes(keyValue)) {
                pressedKeys.push(keyValue);
            }
            updateKeysStyle();
            if (!intervalId) {
                intervalId = setInterval(emitKeys, 50); // Send every 50ms (20 Hz)
            }
        });

        key.addEventListener('mouseup', function() {
            var keyValue = this.getAttribute('data-key');
            pressedKeys = pressedKeys.filter(k => k !== keyValue);
            updateKeysStyle();
            if (pressedKeys.length === 0) {
                clearInterval(intervalId);
                intervalId = null;
            }
        });
    });

    document.addEventListener('keydown', function(event) {
        var key = event.key;
        var code = event.code;
        if (['w', 'a', 's', 'd', 'Shift'].includes(key)) {
            if (!pressedKeys.includes(key)) {
                pressedKeys.push(key);
                updateKeysStyle();
                if (!intervalId) {
                    intervalId = setInterval(emitKeys, 5); // Send every 5ms (200 Hz)
                }
            }
        }
    });

    document.addEventListener('keyup', function(event) {
        var key = event.key;
        var code = event.code;
        if (['w', 'a', 's', 'd', 'Shift'].includes(key)) {
            pressedKeys = pressedKeys.filter(k => k !== key);
            updateKeysStyle();
            if (pressedKeys.length === 0) {
                clearInterval(intervalId);
                intervalId = null;
            }
        }
    });
});
