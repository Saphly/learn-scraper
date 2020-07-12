# learn-scraper

Download all files from all courses enrolled as a student in [Learn](https://www.learn.ed.ac.uk). Requires [Python 3.8.x](https://www.python.org/downloads/).

# Installation

* Clone this repo.

* Install `pipenv` by running the following command: ```pip install --user pipenv```

* `cd` into the repo, and run the following command: ```pipenv install```

# Configuration

* Copy `config.py.template` and rename it as `config.py`: ```cp config.py.template config.py```

* Replace placeholder values in `config.py` with user-specific ones.

# Usage

* Login to [Learn](https://www.learn.ed.ac.uk) via your browser.

* Click on the `Manage Course List` button, as shown below: 

![Manage Course List button on Learn](docs/manage_course_list.png)

* Under the `TERMS` tab, tick all `Select All/Unselect All` checkboxes, as shown below:

![Ticking all Select All/Unselect All checkboxes](docs/select_all_terms.png)`

* Scroll down to the `Courses in which you are enrolled` tab, and tick *at least* one checkbox for each course whose materials you wish to bulk download. For example:

![Ticking at least one checkbox per course](docs/enrolled_courses.png)

* Click the `Submit` button on the bottom-right corner to finalise your changes.

* `cd` into the repo (if you're not there already), and run the following command: ```python scraper.py```.

# Troubleshooting

## `ModuleNotFoundError`

* If the above command doesn't work, try ```pipenv run python scraper.py``` instead.

## `command not found: pipenv`

* ```pip install --user pipenv``` installs `pipenv` under `$HOME/.local/bin` by default, so make sure this is in your `$PATH`. See [here](https://opensource.com/article/17/6/set-path-linux) for more details.
