PREFIX = ~/.micropython/lib

all:

# Installs all modules to a lib location, for development testing
CMD="find . -maxdepth 1 -mindepth 1 \( -name '*.py' -not -name 'test_*' -not -name 'setup.py' -not -name 'example_*' \) -or \( -type d -not -name 'dist' -not -name 'benchmark' -not -name '*.egg-info' -not -name '__pycache__' \)| xargs --no-run-if-empty cp -r -t $(PREFIX)"
install:
	@mkdir -p $(PREFIX)
	@if [ -n "$(MOD)" ]; then \
	    for m in $(MOD); do \
	      (cd $$m; sh -c $(CMD)); \
	    done \
	else \
	    for d in $$(find -maxdepth 1 -type d ! -name ".*" -a ! -name "cpython-*"); do \
	        echo $$d; \
	        (cd $$d; sh -c $(CMD)); \
	    done \
	fi
