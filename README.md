# AGFEO Contact Synchroniser

This project replicates contacts from **Exchange** and **Sage 50 Handwerk** to a **AGFEO PBX**.

## Plugins

All plugins return a dictionary of contacts. The key of the dictionary is always the unique id of the source (for
example a database id) and the value is the contact as VCARD.

### Exchange

The contacts of an exchange account are read and replicated to the agfeo pbx. The code should be easily refactored or
changed for example public folders.

### Sage

The customer I have written this project for used **Sage 50 Handwerk** as ERP. All contacts in this erp system are also
read and written into the pbx.

## Installation

In my case I run this project as **scheduled task** on windows. First you have to download this repository and install
the venv (PowerShell):

```
git clone https://github.com/HyP3r-/agfeo-contact-synchroniser.git
cd agfeo-contact-synchroniser
python3 -m venv venv
.\venv\Scripts\activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
```

Then create a scheduled task with this action:

```
C:\Path\To\The\Repository\venv\Scripts\python.exe C:\Path\To\The\Repository\agfeocontactsynchroniser.py
```

## Logging

This project creates a log in the **log** folder.

## Tested AGFEO PBX

This project was developed and tested with a AGFEO ES 548 with firmware version 3.2e.
