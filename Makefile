#
# Makefile for 
#  - running unit tests
#  - building RPM and other packages
#

VERSION=9.2.0
RELEASE=1
MVN=mvn -q

TESTS = $(wildcard tests/test_*.py)

export PYTHONPATH := lib:.:tests

PYTHON=python3

# by default, test and build everything
default: test all

test: init runtest

init:
	mkdir -p build
	mkdir -p target

.PHONY: runtest $(TESTS)

runtest: $(TESTS)

$(TESTS):
	@echo "\n** Running test $@"
	@${PYTHON} $@

#
# packaging
#

#
# this has to be executed once per BSS
# arg = TSI package name
#
define prepare-specific
mkdir -p target
mkdir -p build
rm -rf build/*
cp -R docs build-tools/* build/
mkdir -p build/lib
mkdir -p build/src/main/package/distributions/Default/src/etc/unicore/tsi
mkdir -p build/src/main/package/distributions/Default/src/var/log/unicore/tsi
mkdir -p build/src/main/package/distributions/Default/src/usr/share/unicore/tsi
cp lib/* build/lib
cp CHANGES.md LICENSE build/docs/
cp build-tools/conf.properties.bssspecific build/src/main/package/conf.properties
sed -i "s/name=tsi/name=$1/" build/src/main/package/conf.properties
sed -i "s/VERSION/${VERSION}/" build/pom.xml
sed -i "s/__VERSION__/${VERSION}/" build/lib/TSI.py
mv build/src/main/package/distributions/Debian/debian/unicore-tsi.service build/src/main/package/distributions/Debian/debian/unicore-$1.service
mv build/src/main/package/distributions/RedHat/src/usr/lib/systemd/system/unicore-tsi.service build/src/main/package/distributions/RedHat/src/usr/lib/systemd/system/unicore-$1.service
endef

#
# arg = dir with bss specific files, 
#
define copy-bssfiles
cp -p $1/* build/lib
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
# Everything
#
all: nobatch-all torque-all slurm-all lsf-all ll-all tgz

#
# Generic binary tgz containing everything required to install the TSI
# using the Install.sh script
#
tgz:
	@echo "Building target/unicore-tsi-${VERSION}.tgz ..."
	@mkdir -p target
	@mkdir -p build
	@rm -rf build/*
	@cp -R build-tools docs lib loadleveler lsf slurm build/
	@cp README.md CHANGES.md LICENSE Install.sh build/
	@sed -i "s/__VERSION__/${VERSION}/" build/lib/TSI.py
	@tar czf target/unicore-tsi-${VERSION}.tgz --xform="s%^build/%unicore-tsi-${VERSION}/%" --exclude-vcs build/*


clean:
	@find -name "*~" -delete
	@find -name "*.pyc" -delete
	@find -name "__pycache__" -delete
	@rm build -rf

realclean: clean
	@rm target -rf

