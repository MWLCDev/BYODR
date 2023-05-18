from flask import Flask, render_template
import subprocess

app = Flask(__name__)


@app.route("/")
def index():
    # Render the HTML file
    return render_template("index.html")


@app.route("/run_draw_map_python")
def run_draw_map_python():
    try:
        # Execute the Python script
        subprocess.call(
            ["python", "./plot_training_sessions_map/draw_training_sessions.py"]
        )
        return "Script executed successfully!", 200
    except Exception as e:
        return f"Error executing the script: {str(e)}", 500


if __name__ == "__main__":
    app.run()
