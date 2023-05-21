from flask import Flask, render_template, url_for, jsonify
import subprocess
from plot_training_sessions_map.draw_training_sessions import main

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
        result = main()  # Call main() to get the result
        sent_list = {}
        for x in result:
            new_key = x
            new_age = url_for(
                "static",
                filename=f"training_maps/{x}.html",
                _external=True,
            )
            sent_list[new_key] = new_age
        json_sent_list = jsonify(sent_list)
        return json_sent_list
    except Exception as e:
        return f"Error executing the script: {str(e)}", 500


if __name__ == "__main__":
    app.run()
