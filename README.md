# UNICORE Target System Interface (TSI)

[![Test](https://github.com/UNICORE-EU/tsi/actions/workflows/tsi-build.yml/badge.svg)](https://github.com/UNICORE-EU/tsi/actions/workflows/tsi-build.yml)


This repository contains the source code for the UNICORE TSI server, which is the component used to
interface to a resource manager such as Slurm and to access files on the cluster.

This server will usually run with elevated privileges (as "root" or via "setpriv")
on one or more of the cluster's login nodes.

## Downloads

[TSI releases](https://github.com/UNICORE-EU/tsi/releases) are done either as a generic tar.gz file with an Install.sh
script for installation, for Slurm, as rpm or deb packages. The TSI is also included in the
[Server bundle](https://github.com/UNICORE-EU/server-bundle/releases)


## Documentation

See the [TSI manual](https://unicore-docs.readthedocs.io/en/latest/admin-docs/tsi/index.html)

## Prerequisites

The TSI requires Python 3

It requires an open port (default: 4433) where it receives connections
from the UNICORE/X server(s). The TSI will make outgoing connections
(callbacks) to the UNICORE/X server(s). Please set up your firewall(s)
accordingly. Operation through an SSH tunnel is possible as well, see
the manual for details.

## Building

Use the supplied Makefile to run tests and / or build packages for
the various supported batch systems.

You will need Java, Maven and Ant to build RPM/DEB packages.

Run

    make <bss>-<type>

where `bss` is one of: slurm, nobatch, torque, lsf
and `type` is one of: tgz, deb, rpm

for example

    make slurm-rpm


To build a generic tar.gz suitable for installation
using the `./Install.sh` script

    make tgz
