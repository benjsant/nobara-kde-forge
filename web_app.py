#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NobaraForgeKDE - Interface web Flask."""

from flask import Flask, render_template

from routes import legacy, profiles, kde_settings, state_routes, system, themes, login_manager, laptop, nobara_tools
from routes.shared import log_info

app = Flask(__name__,
            template_folder='web/templates',
            static_folder='web/static')
app.json.sort_keys = False

app.register_blueprint(legacy.bp)
app.register_blueprint(profiles.bp)
app.register_blueprint(kde_settings.bp)
app.register_blueprint(state_routes.bp)
app.register_blueprint(system.bp)
app.register_blueprint(themes.bp)
app.register_blueprint(login_manager.bp)
app.register_blueprint(laptop.bp)
app.register_blueprint(nobara_tools.bp)


@app.route('/')
def index():
    return render_template('index.html')


def main():
    log_info("NobaraForgeKDE demarre sur http://localhost:5000")
    app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)


if __name__ == '__main__':
    main()
