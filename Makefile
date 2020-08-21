#
# Makefile for 
#  - running unit tests
#  - building RPM and other packages
#  - creating and deploying documentation  
#

VERSION=8.0.4
RELEASE=1
DOCVERSION=8.0.4
MVN=mvn

VERSION ?= ${DEFAULT_VERSION}
DOCVERSION ?= ${DEFAULT_DOCVERSION}
RELEASE ?= ${DEFAULT_RELEASE}


TESTS = $(wildcard tests/*.py)

export PYTHONPATH := lib:.:tests

# if you do not want Python2 tests, set the following to "/bin/true"
PYTHON=python
# if you do not want Python3 tests, set the following to "/bin/true"
PYTHON3=python3

# by default, test and build everything
default: test packages

test: init runtest

init:
	mkdir -p build
	mkdir -p target

.PHONY: runtest $(TESTS)

runtest: $(TESTS)

$(TESTS):
	@echo "\n** Running test $@"
	@${PYTHON} $@
	@${PYTHON3} $@

#
# documentation
#
DOCOPTS=-Ddocman.enabled -Ddoc.relversion=${DOCVERSION} -Ddoc.compversion=${DOCVERSION} -Ddoc.src=docs/manual.txt -Ddoc.target=tsi-manual

doc-generate:
	mkdir -p target
	if [ ! -d target/docman ] ; then svn export https://svn.code.sf.net/p/unicore/svn/tools/docman/trunk target/docman --force ; fi 
	ant -f target/docman/doc-build.xml -lib target/package/tools ${DOCOPTS} doc-all

doc-deploy:
	ssh bschuller@unicore-dev.zam.kfa-juelich.de sudo rm -rf /var/www/documentation/tsi-${DOCVERSION}
	ssh bschuller@unicore-dev.zam.kfa-juelich.de sudo mkdir /var/www/documentation/tsi-${DOCVERSION}
	ssh bschuller@unicore-dev.zam.kfa-juelich.de mkdir -p tsidoc-${DOCVERSION}
	scp target/site/* bschuller@unicore-dev.zam.kfa-juelich.de:tsidoc-${DOCVERSION}
	ssh bschuller@unicore-dev.zam.kfa-juelich.de sudo mv tsidoc-${DOCVERSION}/* /var/www/documentation/tsi-${DOCVERSION}

doc: doc-generate doc-deploy


#
# packaging
#

#
# this has to be executed once per BSS
# arg = TSI package name
#
define prepare-specific
mkdir -p target
rm -rf build/*
mkdir -p build/lib
cp -R docs build-tools/* build/
cp lib/* build/lib
cp CHANGES LICENCE build/docs/
cp build-tools/conf.properties.bssspecific build/src/main/package/conf.properties
sed -i "s/name=tsi/name=$1/" build/src/main/package/conf.properties
sed -i "s/VERSION/${VERSION}/" build/pom.xml
sed -i "s/__VERSION__/${VERSION}/" build/lib/TSI.py
mv build/src/main/package/distributions/Debian/debian/unicore-tsi.service build/src/main/package/distributions/Debian/debian/unicore-$1.service
mv build/src/main/package/distributions/RedHat/src/usr/lib/systemd/system/unicore-tsi.service build/src/main/package/distributions/RedHat/src/usr/lib/systemd/system/unicore-$1.service
find build | grep .svn | xargs rm -rf
endef

#
# arg = dir with bss specific files, 
#
define copy-bssfiles
cp -p $1/* build/lib
find build | grep .svn | xargs rm -rf
endef

#
# generic rules for building deb and prm
#

%-deb: %-prepare
	cd build && ${MVN} package -Ppackman -Dpackage.type=deb -Ddistribution=Debian -Dpackage.version=${VERSION} -Dpackage.release=${RELEASE}
	cp build/target/*.deb target/

%-rpm: %-prepare
	cd build && ${MVN} package -Ppackman -Dpackage.type=rpm -Ddistribution=RedHat -Dpackage.version=${VERSION} -Dpackage.release=${RELEASE}
	cp build/target/*.rpm target/

%-tgz: %-prepare
	cd build && ${MVN} package -Ppackman -Dpackage.type=bin.tar.gz -Dpackage.version=${VERSION} -Dpackage.release=${RELEASE}
	cp build/target/*.tar.gz target/


#
# attempts to build all packages (even if they are the "wrong" kind on the current OS)
#
%-all: %-deb %-rpm %-tgz
	echo "Done."

#
# builds the correct package for the current OS
#
%-package: %-prepare
	cd build && ${MVN} package -Ppackman -Dpackage.version=${VERSION} -Dpackage.release=${RELEASE}
	cp build/target/unicore* target/
	echo "Done."

#
# No-batch
#
nobatch-prepare: clean
	$(call prepare-specific,tsi-nobatch)

#
# Torque
#
torque-prepare: clean
	$(call prepare-specific,tsi-torque)
	$(call copy-bssfiles,torque)

#
# Slurm
#
slurm-prepare: clean
	$(call prepare-specific,tsi-slurm)
	$(call copy-bssfiles,slurm)

#
# LSF
#
lsf-prepare: clean
	$(call prepare-specific,tsi-lsf)
	$(call copy-bssfiles,lsf)

#
# LL
#
ll-prepare: clean
	$(call prepare-specific,tsi-loadleveler)
	$(call copy-bssfiles,loadleveler)

#
# All the linux packages for the current OS
#
packages: nobatch-package torque-package slurm-package lsf-package ll-package

#
# Really everything except doc
#
all: nobatch-all torque-all slurm-all lsf-all ll-all tgz

#
# Generic binary tgz containing everything required to install the TSI
# using the Install.sh script
#
tgz:
	@mkdir -p target
	@mkdir -p build
	@rm -rf build/*
	@cp -R build-tools docs lib loadleveler lsf slurm build/
	@cp README CHANGES LICENCE Install.sh build/
	@sed -i "s/__VERSION__/${VERSION}/" build/lib/TSI.py
	@tar czf target/unicore-tsi-${VERSION}.tgz --xform="s%^build/%unicore-tsi-${VERSION}/%" --exclude-vcs build/*

#
# clean
#

clean:
	@find -name "*~" -delete
	@find -name "*.pyc" -delete
	@find -name "__pycache__" -delete
	@rm build -rf
	@rm target -rf
