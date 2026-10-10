from dotenv import load_dotenv
load_dotenv()

from app import flask_app

if __name__ == "__main__":
    flask_app.run(debug=True)