===============================
Introduction
===============================

Overview
--------

The QM33xxx/DW3xxx IC is a radio transceiver IC (a family of transceivers including DW3000, DW3300q, DW3720, QM33120) implementing the UWB HRP physical layer defined in IEEE 802.15.4 standard [3].  

For more details of this device the reader is referred to:

* The Data Sheet [1]

* The User Manual [2]

This document, 'DW3xxx Device Driver - Application Programming Interface (API) Guide' is a guide to the device driver software developed by Qorvo to drive the family of UWB radio transceiver ICs.    

The device driver is essentially a set of low-level functions providing a means to exercise the main features of the transceiver without having to deal with the details of accessing the device directly through its SPI interface register set.

The device driver is provided as source code to allow it to be ported to any target microprocessor system with an SPI interface.  The source code employs the C programming language.  

The device driver is controlled through its Application Programming Interface (API) which is comprised of a set of functions.  This document is predominately a guide to the device driver API describing each of the API functions in detail in terms of its parameters, functionality and utility.
