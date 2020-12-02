# UNICORE Target System Interface (TSI)

This is the UNICORE TSI server, used to interface to a
resource manager such as Slurm and to access files on the
cluster.

This server will run as "root" on the cluster login node(s).

## Prerequisites

The TSI requires Python 3.4 or later

It requires an open port (default: 4433) where it receives connections
from the UNICORE/X server(s). The TSI will make outgoing connections
(callbacks) to the UNICORE/X server(s). Please set up your firewall(s)
accordingly. Operation through an SSH tunnel is possible as well, see
the manual for details.

## Installation

This generic TSI distribution contains several TSI variations for several 
popular batch systems.

Before being able to use the TSI, you must install one of the TSI variants 
and configure it for your local environment.

 * Execute the installation script +Install.sh+ and follow the instructions 
   to copy all required files into a new TSI installation directory.

 * Carefully review the tsi.properties and startup.properties files


## Operation

The TSI is started/stopped via the scripts in the bin/ directory.
