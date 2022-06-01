.PHONY: cirrs rmkg restart reset mdg syll-test syllabs

SYLROOT="./isu/"
# SYLROOT="./isu/Институт-математики-и-информационных-технологий/"
# SYLROOT="./isu/Институт-математики-и-информационных-технологий/01.03.02--Прикладная-математика-и-информатика-/Математическое-моделирование/очная/2021"
msg:
	echo "Use explicit target"

restart: reset cirrs syll-test

reset: rmkg

cirrs:
	./allcirrs.sh

syll-test:
	python syllabus.py

rmkg:
	rm -f ../kg/*


syllabs:
	./allwps.sh $(SYLROOT)
