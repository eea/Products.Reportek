# Script (Python) "test_ping"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=
# title=
##
# Example code:


if container.ReportekEngine.canPingCR():
    context.getMySelf().content_registry_ping()
