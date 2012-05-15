:mod:`Products.Reportek.OpenFlowEngine` --- OpenFlowEngine module
=================================================================

The workflow state information is being part of the envelope. If you
want to get information on the state you look at the envelope.

When an envelope is created, the user must reserve the envelope for
himself to work on. This takes care of responsibility of the task. The
user does this by clicking on the “Activate” button. Once he has
done this, a new set of buttons appear on the main page of the envelope
relevant for the task at hand. If the task is to upload files, then
buttons for upload and delete files appear.

When the user is satisfied that he has uploaded all files, he clicks
on the “Complete” button, and the envelope is moved to the next
state. This could be an inspect stage. This is configurable. In the
inspect stage another user or the same clicks on the “Activate”
button and the procedure repeats.

If the user discovers that he can't complete the work on his own, he
can deactivate the task and someone else can pick it up and activate it.

Several activities could be going on at the same time on an envelope, so
most of the state information is located in the workitem object. There
is one or more of these enclosed in the envelope. They serve both to
show the current activities and the history of the envelope.


Choosing a process
------------------

As mentioned earlier, a workflow is assigned to an envelope depending on
which dataflow and which country it is. An envelope can be tagged with
more than one dataflow. There are good reasons why the countries have
asked for a way to tag a delivery with multiple dataflows. For instance,
ME-1 is a combination of 5 or more dataflows, which exist individually
in ROD. The countries must report on different obligations to satisfy
ME-1. For instance Romania must report on the Black Sea obligation,
whereas Poland must report on the Baltic Sea obligation.

Unfortunately, multiple dataflows conflicts with the workflows. If
a delivery is tagged with two dataflows that specify two different
workflows, which one to choose? Or is it possible to somehow combine
the workflows? We chose to not try to be smart.

This means Reportek shall not accept a combination of dataflows that
results in a choice of two different workflow processes. To exemplify:
If a delivery is tagged with dataflow X and Y, and X results in the
"default" workflow process to be chosen, and Y results in the "Z" workflow
process to be chosen, then creation of the envelope must fail. It could
be possible to specify a combinatory rule, meaning in case a dataflow
is tagged with X and Y, then the “W” workflow process is to be used.

:class:`Products.Reportek.OpenFlowEngine` --- OpenFlowEngine core class
-----------------------------------------------------------------------

.. automodule:: Products.Reportek.OpenFlowEngine
   :members:

:class:`Products.Reportek.xpdl2openflow` --- xpdl2openflow class
----------------------------------------------------------------

.. automodule:: Products.Reportek.xpdl2openflow
   :members:

:class:`Products.Reportek.xpdldefinitions` --- xpdldefinitions class
--------------------------------------------------------------------

.. automodule:: Products.Reportek.xpdldefinitions
   :members:

:class:`Products.Reportek.xpdlparser` --- xpdlparser class
----------------------------------------------------------

.. automodule:: Products.Reportek.xpdlparser
   :members:

