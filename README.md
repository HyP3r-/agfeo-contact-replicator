# AGFEO Contact Replicator
This project replicates contacts from Exchange and Sage 50 Handwerk to a AGFEO PBX.  

## Plugins
All plugins return a dictionary of contacts. The key of the dictionary is always the unique id of the source (for example a database id) and the value is the contact as VCARD.

### Exchange
The contacts of an exchange account are read and replicated to the agfeo pbx. The code should be easily refactored or changed for example public folders.

### Sage
The customer I have written this project for used Sage 50 Handwerk as ERP. All contacts in this erp system are also read and written into the pbx.
