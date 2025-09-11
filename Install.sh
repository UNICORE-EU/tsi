#!/bin/bash

#
# Install script for the TSI (general package)
#
#   Copies platform specific TSI files into a user-chosen directory
#
# Called without parameters, the user will be asked which TSI to install.
# 
# This script can also be called non-interactively using
#   
#   Install.sh <tsi_choice> <install_dir> [<run_user>]
# 
# where
#   'tsi_choice':  one of the platform specific TSIs
#   'install_dir': the destination directory
#   'run_user':    the user to run the TSI as, if 'setpriv' is available
#                  (defaults to 'unicore')
#
# Example:
#   Install.sh slurm /opt/unicore/tsi_slurm
# will install the Slurm TSI into '/opt/unicore/tsi_slurm'
#

# make sure we're in the correct base directory
cd $(dirname $0)

#
# list of all TSIs
#
alltsis="nobatch torque slurm lsf loadleveler"

#
# list all TSIs
#
listTSIs() {
  echo ""
  echo "Available TSI implementations are:"
  echo ""
  i=0
  for tsi in $alltsis; do
      i=`expr $i + 1`
      echo "$i: $tsi"
  done
}

#
# let the user select one TSI for installation
#
choose() {
  echo ""
  echo "The installation will copy all required files into a new directory."
  echo "Files common to all TSI implementations are copied from"
  echo "bin, conf and doc."
  echo ""
  echo "Select a TSI to install (enter number)"
  read input
  i=0
  for tsi in $alltsis; do
      i=`expr $i + 1`
      if [ $i = $input ]; then
        FOUND="true"
        break
      fi
  done
  if [ -z "$FOUND" ]
  then
    echo "Invalid selection"
    exit 1
  fi
}

#
# get the installation directory from the user
# as default, $installdir is offered
#
getdir() {
  installdir=/usr/share/unicore/tsi-$tsi
  echo ""
  echo "Enter installation directory for $tsi (relative or absolute path) [$installdir]"
  read indir
  if [ "$indir" != "" ]; then
    installdir=$indir
  fi
}

#
# get the TSI owner name / runtime username from the user
# as default, $runuser is offered
#
getuser() {
  echo ""
  echo "Enter username who will run the TSI [$1]"
  read runas
  if [ "$runas" != "" ]; then
    runuser=$runas
  fi
}

#
# let the user confirm the installation
#
confirm_tsi() {
  echo ""
  echo "Please confirm installation of $1 into directory $2 by typing y/n [y]"
  read yesno
  case $yesno in
    y*|Y*) echo "";;
    "") echo "";;
    n*|N*) echo "Installation stopped because of missing confirmation"; exit 1;;
    *) echo "Installation stopped because of doubtful confirmation"; exit 1;;
  esac
}

#
# copy files from directory $1 to $2
# - if VERBOSE is non-zero, actions will be echoed
# - if CHECKEXIST is non-zero, existing files will be backed up
#
copy_dir() {
  for file in $1/*; do
    DEST="$2/`basename $file`"

    [ "$VERBOSE" != "" ] && echo "Copy $file to $DEST"

    if [ "$CHECKEXIST" != "" ]
    then     
      if [ -e "$DEST" ]
      then
         diff -q $file $DEST
         if [ $? -ne 0 ]
         then
           echo " ** $DEST exists, saving as ${DEST}.bak"
           cp $DEST ${DEST}.bak
         fi
      fi 
    fi
    cp $file $2
  done
}

#
# INSTALL
#
interactive="true"

tsi=$1
if [ "$tsi" = "" ]; then
  listTSIs
  choose
else
  interactive="false"
fi

installdir=$2
if [ "$installdir" = "" ]; then
  getdir
  confirm_tsi $tsi $installdir
fi


#
# check existence of $installdir
#
if [ -d $installdir ]; then
  if [ "$2" == "" ]; then
    echo "Installation directory $installdir already exists"
    confirm_tsi $tsi $installdir
    echo ""
    echo "Files from $installdir will be overwritten"
    echo ""
    chmod -R u+w $installdir
  fi
elif [ -f $installdir ]; then
  echo "Installation directory $installdir identical to existing file."
  echo "Installation stopped because of doubtful confirmation,"
  echo "Remove file $installdir first."
  exit 1
fi

#
# if this script runs as 'root', query for runtime user
#
if [ "$(id -u)" -eq "0" ]
then
  setpriv=$(which setpriv)
  runuser=${3:-unicore}
  if [ "$setpriv" != "" ]
  then
    if [ "$interactive" = "true" ]; then
      echo ""
      echo "Please select which user will own the TSI files,"
      echo "and be used as the runtime user via 'setpriv'"
      echo "Use 'root' to run the TSI as root."
      getuser $runuser
      echo "Installing for $runuser"
    fi
  fi
fi

#
# generate installation directory
#
mkdir -p $installdir
mkdir -p $installdir/logs
mkdir -p $installdir/bin
mkdir -p $installdir/conf
mkdir -p $installdir/lib

#
# copy common files
#
VERBOSE="true"
CHECKEXIST="true"
echo "Copy common files (bin,conf) first:"
copy_dir build-tools/src/main/package/executableTemplates $installdir/bin
copy_dir build-tools/src/main/package/configTemplates $installdir/conf

tmpdir=/tmp/tsi_install`date +_%H_%M_%S`/lib
mkdir -p $tmpdir

#
# copy Python files
#
VERBOSE=""
CHECKEXIST=""
echo "Copy shared Python files (common to all installations)"
copy_dir lib $tmpdir
if [ "$tsi" != "nobatch" ] ; then 
    echo "Adding batch-system specific files"
    copy_dir $tsi $tmpdir
fi
VERBOSE="true"
CHECKEXIST="true"
echo "Copy Python files into final install dir"
copy_dir $tmpdir $installdir/lib
rm -rf $tmpdir

#
# replace variables in the config files
#
for file in $installdir/conf/* $installdir/bin/* ; do
    sed -i "s%@lib@%$installdir/lib%g" $file
    sed -i "s%@etc@%$installdir/conf%g" $file
    sed -i "s%@log@%$installdir/logs%g" $file
    sed -i "s%@pid@%$installdir/LAST_PID%g" $file
    sed -i "s%@cdInstall@%cd $installdir%g" $file
    sed -i "s%@runuser@%$runuser%g" $file
    sed -i "s%@setpriv@%$setpriv%g" $file
done

#
# set file permissions
#
if [ "$setpriv" != "" ]
then
  chown -R $runuser:$runuser $installdir
fi
chmod 755 $installdir
chmod 700 $installdir/*
chmod 755 $installdir/lib
chmod 700 $installdir/bin/*
chmod 644 $installdir/lib/*
chmod 600 $installdir/conf/*

if [ "$interactive" = "true" ]; then
  echo ""
  echo "##########################################################"
  echo "Finish installation by editing $installdir/conf/tsi.properties."
  echo "##########################################################"
  echo ""
fi
