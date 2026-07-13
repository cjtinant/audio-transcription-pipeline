.PHONY: install

install:
	mkdir -p ~/bin
	ln -sf "$(CURDIR)/transcribe.sh" ~/bin/transcribe
	chmod +x transcribe.sh
