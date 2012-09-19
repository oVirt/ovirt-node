PLANS=$(shell find . -name \*.plan)
SUITES=$(shell find . -name \*.suite)
SETS=$(shell find . -name \*.set)

YAMLFILES=$(PLANS) $(SUITES) $(SETS)

check:
	python check_yaml.py $(YAMLFILES)
	@echo -e "---\n Passed\n---"
