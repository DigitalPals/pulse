// Console Stream Handler
console.log("Console Stream Handler loaded");
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM Content Loaded - initializing console stream");
    
    // Wait a moment for the page to fully load
    setTimeout(function() {
        // Get the console output element
        const consoleOutput = document.getElementById('console-output');
        const consoleStatus = document.getElementById('console-status');
        
        // Update status to connecting
        if (consoleStatus) {
            consoleStatus.textContent = 'Connecting...';
            consoleStatus.className = 'badge badge-warning';
        }
        
        // Clear the "Connecting to console stream..." message
        if (consoleOutput) {
            consoleOutput.innerHTML = '';
        }
        
        // Check if EventSource is supported
        if (typeof EventSource === 'undefined') {
            console.error('EventSource is not supported in this browser');
            if (consoleOutput) {
                const messageElement = document.createElement('div');
                messageElement.className = 'console-message error';
                messageElement.innerHTML = '<span class="timestamp">' + new Date().toISOString().replace('T', ' ').substr(0, 19) + '</span><i class="fas fa-exclamation-triangle"></i> Your browser does not support Server-Sent Events. Please use a modern browser.';
                consoleOutput.appendChild(messageElement);
            }
            return;
        }
        
        // Variables to track connection status
        let connectionEstablished = false;
        let connectionTimeout = null;
        
        // Function to check connection status
        function checkConnection() {
            if (!connectionEstablished) {
                console.warn("Connection not established after timeout, attempting to reconnect");
                if (consoleOutput) {
                    const messageElement = document.createElement('div');
                    messageElement.className = 'console-message warning';
                    messageElement.innerHTML = '<span class="timestamp">' + new Date().toISOString().replace('T', ' ').substr(0, 19) + '</span><i class="fas fa-exclamation-circle"></i> Connection timeout. Attempting to reconnect...';
                    consoleOutput.appendChild(messageElement);
                    consoleOutput.scrollTop = consoleOutput.scrollHeight;
                }
                
                // Close existing connection if any
                if (window.activeEventSource) {
                    window.activeEventSource.close();
                }
                
                // Try to reconnect
                connectToStream();
            }
        }
        
        // Set a timeout to check connection status
        connectionTimeout = setTimeout(checkConnection, 10000); // 10 seconds timeout
        
        // Connect to the SSE endpoint
        function connectToStream() {
            try {
                console.log("Attempting to connect to /console-stream");
                const eventSource = new EventSource('/console-stream');
                window.activeEventSource = eventSource; // Store reference globally
                console.log("EventSource created");
                
                // Handle connection open
                eventSource.onopen = function(event) {
                    console.log("EventSource connection opened", event);
                    connectionEstablished = true;
                    
                    // Clear the connection timeout
                    if (connectionTimeout) {
                        clearTimeout(connectionTimeout);
                        connectionTimeout = null;
                    }
                    
                    if (consoleStatus) {
                        consoleStatus.textContent = 'Connected';
                        consoleStatus.className = 'badge badge-success';
                    }
                    
                    // Add a connected message
                    if (consoleOutput) {
                        const messageElement = document.createElement('div');
                        messageElement.className = 'console-message info';
                        messageElement.innerHTML = '<span class="timestamp">' + new Date().toISOString().replace('T', ' ').substr(0, 19) + '</span><i class="fas fa-info-circle"></i> Connected to console stream';
                        consoleOutput.appendChild(messageElement);
                        consoleOutput.scrollTop = consoleOutput.scrollHeight;
                    }
                };
                
                // Handle messages
                eventSource.addEventListener('message', function(event) {
                    console.log("EventSource message received", event);
                    try {
                        const data = JSON.parse(event.data);
                        console.log("Parsed message data:", data);
                        
                        if (consoleOutput) {
                            const messageElement = document.createElement('div');
                            messageElement.className = 'console-message ' + (data.type || 'info');
                            
                            // Add timestamp
                            const timestampSpan = document.createElement('span');
                            timestampSpan.className = 'timestamp';
                            timestampSpan.textContent = data.timestamp || new Date().toISOString().replace('T', ' ').substr(0, 19);
                            messageElement.appendChild(timestampSpan);
                            
                            // Add message with appropriate icon
                            let icon = '';
                            if (data.type === 'error') {
                                icon = '<i class="fas fa-exclamation-triangle"></i> ';
                            } else if (data.type === 'warning') {
                                icon = '<i class="fas fa-exclamation-circle"></i> ';
                            } else {
                                icon = '<i class="fas fa-info-circle"></i> ';
                            }
                            
                            const messageContent = document.createElement('span');
                            messageContent.className = 'message-content';
                            messageContent.innerHTML = icon + data.message;
                            messageElement.appendChild(messageContent);
                            
                            // Add to console output
                            consoleOutput.appendChild(messageElement);
                            
                            // Auto-scroll to bottom
                            consoleOutput.scrollTop = consoleOutput.scrollHeight;
                        }
                    } catch (e) {
                        console.error('Error parsing message:', e);
                    }
                });
                
                // Handle errors
                eventSource.onerror = function(event) {
                    console.error("EventSource error", event);
                    if (consoleStatus) {
                        consoleStatus.textContent = 'Disconnected';
                        consoleStatus.className = 'badge badge-danger';
                    }
                    
                    // Add an error message
                    if (consoleOutput) {
                        const messageElement = document.createElement('div');
                        messageElement.className = 'console-message error';
                        messageElement.innerHTML = '<span class="timestamp">' + new Date().toISOString().replace('T', ' ').substr(0, 19) + '</span><i class="fas fa-exclamation-triangle"></i> Connection to console stream lost. Refresh the page to reconnect.';
                        consoleOutput.appendChild(messageElement);
                        consoleOutput.scrollTop = consoleOutput.scrollHeight;
                    }
                    
                    // Close the connection
                    eventSource.close();
                };
                
                // Clean up when leaving the page
                window.addEventListener('beforeunload', function() {
                    eventSource.close();
                });
            } catch (e) {
                console.error('Error connecting to console stream:', e);
                
                // Add an error message
                if (consoleOutput) {
                    const messageElement = document.createElement('div');
                    messageElement.className = 'console-message error';
                    messageElement.innerHTML = '<span class="timestamp">' + new Date().toISOString().replace('T', ' ').substr(0, 19) + '</span><i class="fas fa-exclamation-triangle"></i> Failed to connect to console stream: ' + e.message;
                    consoleOutput.appendChild(messageElement);
                }
            }
        }
        
        // Initial connection
        connectToStream();
    }, 500); // Wait 500ms for the page to fully load
});