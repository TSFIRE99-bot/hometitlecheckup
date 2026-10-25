"""HomeKeep. Vercel finds the Flask `app` here. On your computer: `flask --app app run --debug`."""
from web import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
