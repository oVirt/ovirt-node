
PYTHONSOURCES=$(shell find . -name \*.py -not -path */hacks.py)
XMLSOURCES=$(shell find . -name \*.xml -or -name \*.xsl)
CLEANFILES=$(shell find . -name \*.pyc -o -name \*.pyo -o -name \*~ -o -name MANIFEST)


check-local: syntax-checks doctests
	@echo -e "---\n Passed all.\n---"


syntax-checks: pep8 pyflakes
	@echo -e "---\n Passed syntax checks.\n---"

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
	-rm $(CLEANFILES)
