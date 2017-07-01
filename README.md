# GerritUI
A QT5 based GUI for Gerrit Review service, written in Python, which uses the same SSH interface as git

Requirements
============

* Python 3.x
* PyQt5 (Widgets)
* paramiko (for ssh)
* access to a gerrit host
* a valid unlocked ssh key in ssh-agent

Options
=======
* -h <hostname> 
* -p <ssh port> // default port is 29418
* -u <username> // defaults to your current login
