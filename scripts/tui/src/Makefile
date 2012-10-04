
PYTHONSOURCES=$(shell find . -name \*.py -not -path */hacks.py)
XMLSOURCES=$(shell find . -name \*.xml -or -name \*.xsl)
CLEANFILES=$(shell find . -name \*.pyc -o -name \*.pyo -o -name \*~)

check-local: doctests pep8 pyflakes
	@echo -e "---\n Passed.\n---"

doctests:
	@for M in $(PYTHONSOURCES); \
	do \
		echo Doctest on "$$M"; \
		PYTHONPATH=. python -m doctest $$M || exit 1; \
	done

pep8:
	@for M in $(PYTHONSOURCES); \
	do \
		echo pep8 on "$$M"; \
		PYTHONPATH=. pep8 -r $$M || exit 1; \
	done

PYLINT=pylint -f parseable --include-ids=yes --rcfile=.pylintrc
pylint:
	@for M in $(PYTHONSOURCES); \
	do \
		echo pylint on "$$M"; \
		PYTHONPATH=. $(PYLINT) $$M || exit 1; \
	done

pyflakes:
	@for M in $(PYTHONSOURCES); \
	do \
		echo pyflakes on "$$M"; \
		PYTHONPATH=. pyflakes $$M || exit 1; \
	done

clean:
	echo $(CLEANFILES)
	rm $(CLEANFILES)
