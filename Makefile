.PHONY: cirrs rmkg restart reset mdg syll-test syllabs app curr-test wpgen-test

SYLROOT="/mnt/bck/isu-studprogs-dowloaded/"

# SYLROOT="./isu/Институт-математики-и-информационных-технологий/"
# SYLROOT="./isu/Институт-математики-и-информационных-технологий/01.03.02--Прикладная-математика-и-информатика-/Математическое-моделирование/очная/2021"
msg:
	echo "Use explicit target"

restart: reset cirrs syll-test curr-test wpgen-test

reset: rmkg

cirrs:
	./allcurrs.sh

syll-test:
	python syllabus.py

rmkg:
	rm -f ../kg/*


syllabs:
	./allwps.sh $(SYLROOT)

app:
	FLASK_APP=check FLASK_ENV=development flask run


curr-test:
	python curriculum.py

wpgen-test:
	python wpgen.py
