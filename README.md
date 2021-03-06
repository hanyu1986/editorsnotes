## Installation
Editors' Notes requires Python 2.7 and PostgreSQL.

To set up a local development environment, install [Fabric](http://fabfile.org/) 
and make sure you have the following dependencies

* libxml2
* libxslt
* ElasticSearch
* node.js & npm
* Optional: [Watchdog](http://packages.python.org/watchdog/), for use with the `fab watch_static` command to automatically collect and compile static files as they are changed.

1. Run the command `fab setup` inside the project directory
2. Edit the generated "editorsnotes/settings\_local.py" file with your database information
3. Run `fab sync_database`
4. Start the development server with `fab runserver`

## Browser compatibility
Editors' Notes is tested against the latest versions of Firefox, Chrome, Safari, and Opera, as well as Internet Explorer 10+.

[![browser support](https://ci.testling.com/editorsnotes/editorsnotes.png)
](https://ci.testling.com/editorsnotes/editorsnotes)
