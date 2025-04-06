from flask import Flask, request
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    logger.debug("Entering /login")
    if request.method == 'POST':
        logger.debug("POST request received")
        return "Login POST successful"
    logger.debug("Rendering login page")
    return "Login GET page"

# Index route to redirect to /login
@app.route('/')
def index():
    return redirect('/login')

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8001, debug=True)
