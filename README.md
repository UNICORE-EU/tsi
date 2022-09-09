# UNICORE Target System Interface (TSI)

This repository contains the source code for the
UNICORE TSI server, which is the component used to
interface to a resource manager such as Slurm
and to access files on the cluster.

This server will run as "root" on the cluster login node(s).

## Downloads

TSI code is distributed within the Core server bundle,
and also as a separate generic tar.gz file with an Install.sh script for installation.

Check the SourceForge
[Core server downloads](https://sourceforge.net/projects/unicore/files/Servers/Core)

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
