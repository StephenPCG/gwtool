# Gateway Tool

NOTE: this is my personal toy project, never use it unless you can read through and understand the code.

## Overview

This tool has a long backend based on my years of configuring gateways. However, those histories do not reflect in this repo.
I was using iptables for around a decade, from this tool on, I switched to nftables, and also re-organized the code base.

I used to put all code and configuration in /opt/gateway, however, there are many common code and distinguished configuration
among gateway instances. This tool extracts the common part in to a python package, so that can be installed via simply `pip install`,
while keep all other configurations in /opt/gateway and managed in a seperate repo.

To install:

```
pip install git+https://github.com/stephenpcg/gwtool
```

Add configuration to /opt/gateway, see `example/` directory, and run:

```
gw setup
```
