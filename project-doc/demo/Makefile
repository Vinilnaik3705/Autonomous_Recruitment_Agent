.PHONY: all
all: recruitment-demo.pptx recruitment-report.pdf

recruitment-demo.pptx: slides.md
	pandoc $< --slide-level=1 -o $@

recruitment-report.pdf: report.md report.css
	pandoc $< -t html5 --pdf-engine=weasyprint --css=report.css --metadata title="Recruitment workflow migration" -o $@
