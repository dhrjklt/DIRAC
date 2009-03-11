import sys
@SITEPYTHON@
from DIRAC.Core.Base import Script
Script.parseCommandLine()
##############################################################################################################################
# $Id: JobWrapperTemplate.py,v 1.2 2009/03/11 09:35:06 rgracian Exp $
# Generated by JobAgent version: %s for Job %s on %s.
##############################################################################################################################

from DIRAC.WorkloadManagementSystem.JobWrapper.JobWrapper   import JobWrapper
from DIRAC.WorkloadManagementSystem.Client.JobReport        import JobReport
from DIRAC.Core.DISET.RPCClient                             import RPCClient
from DIRAC                                                  import S_OK, S_ERROR, gConfig, gLogger

import os

class JobWrapperError(Exception):
  def __init__(self, value):
    self.value = value
  def __str__(self):
    return str(self.value)

def rescheduleFailedJob(jobID,message):

    gLogger.warn('Failure during '+message)

    jobManager  = RPCClient('WorkloadManagement/JobManager')
    jobReport = JobReport(int(jobID),'JobWrapperTemplate')

    #Setting a job parameter does not help since the job will be rescheduled,
    #instead set the status with the cause and then another status showing the
    #reschedule operation. 

    jobReport.setJobStatus(  'Failed', message, sendFlag = False )
    jobReport.setApplicationStatus( 'Failed %s ' % message, sendFlag = False )
    jobReport.setJobStatus( minor = 'ReschedulingJob', sendFlag = True )

    gLogger.info('Job will be rescheduled after exception during execution of the JobWrapper')
    result = jobManager.rescheduleJob(int(jobID))
    if not result['OK']:
      gLogger.warn(result)

    return

def execute ( arguments ):

  jobID = arguments['Job']['JobID']
  os.environ['JOBID'] = jobID

  if arguments.has_key('WorkingDirectory'):
    wdir = os.path.expandvars(arguments['WorkingDirectory'])
    if os.path.isdir(wdir):
      os.chdir(wdir)
    else:
      try:
        os.makedirs(wdir)
        if os.path.isdir(wdir):
          os.chdir(wdir)
      except Exception, x:
        gLogger.warn('JobWrapperTemplate could not create working directory with exception:\n '+str(x))
        rescheduleFailedJob(jobID,'Could Not Create Working Directory')
        return

  jobID = arguments['Job']['JobID']
  root = arguments['CE']['Root']
  jobReport = JobReport(int(jobID),'JobWrapper')

  try:
    job = JobWrapper( jobID, jobReport )
    job.initialize(arguments)
  except Exception, x:
    message = 'JobWrapper failed the initialization phase with exception: \n '+str(x)
    gLogger.error(message)
    rescheduleFailedJob(jobID,'Job Wrapper Initialization')
    job.sendWMSAccounting('Failed','Job Wrapper Initialization')
    return

  if arguments['Job'].has_key('InputSandbox'):
    try:
      result = job.transferInputSandbox(arguments['Job']['InputSandbox'])
      if not result['OK']:
        gLogger.warn(result['Message'])
        raise JobWrapperError(result['Message'])
    except Exception, x:
      message = 'JobWrapper failed to download input sandbox with exception: \n '+str(x)
      gLogger.warn(message)
      gLogger.exception()
      rescheduleFailedJob(jobID,'Input Sandbox Download')
      job.sendWMSAccounting('Failed','Input Sandbox Download')
      return
  else:
    gLogger.verbose('Job has no InputSandbox requirement')

  if arguments['Job'].has_key('InputData'):
    if arguments['Job']['InputData']:
      try:
        result = job.resolveInputData(arguments)
        if not result['OK']:
          gLogger.warn(result['Message'])
          raise JobWrapperError(result['Message'])
      except Exception, x:
        message = 'JobWrapper failed to resolve input data with exception: \n '+str(x)
        gLogger.warn(message)
        gLogger.exception()
        rescheduleFailedJob(jobID,'Input Data Resolution')
        job.sendWMSAccounting('Failed','Input Data Resolution')
        return
    else:
      gLogger.verbose('Job has a null InputData requirement:')
      gLogger.verbose(arguments)
  else:
    gLogger.verbose('Job has no InputData requirement')

  try:
    result = job.execute(arguments)
    if not result['OK']:
      gLogger.warn(result['Message'])
      raise JobWrapperError(result['Message'])
  except Exception, x:
    if str(x) == '0':
      gLogger.verbose('JobWrapper exited with status=0 after execution')
      pass
    else:
      message = 'Job failed in execution phase with exception: \n'+str(x)
      gLogger.warn(message)
      gLogger.exception()
      #jobReport  = RPCClient('WorkloadManagement/JobStateUpdate')
      jobReport.setJobStatus('Failed',str(x))
      jobParam = jobReport.setJobParameter('Error Message',message)
      if not jobParam['OK']:
        gLogger.warn(jobParam)
      job.sendWMSAccounting('Failed','Exception During Execution')
      job.sendFailoverRequest()
      return

  if arguments['Job'].has_key('OutputSandbox') or arguments['Job'].has_key('OutputData'):
    try:
      result = job.processJobOutputs(arguments)
      if not result['OK']:
        gLogger.warn(result['Message'])
        raise JobWrapperError(result['Message'])
    except Exception, x:
      message = 'JobWrapper failed to process output files with exception: \n '+str(x)
      gLogger.warn(message)
      gLogger.exception()
      #jobReport  = RPCClient('WorkloadManagement/JobStateUpdate')
      jobParam = jobReport.setJobParameter('Error Message',message)
      if not jobParam['OK']:
        gLogger.warn(jobParam)
      jobStatus = jobReport.setJobStatus('Failed','Uploading Job Outputs')
      if not jobStatus['OK']:
        gLogger.warn(jobStatus['Message'])
      job.sendWMSAccounting('Failed','Uploading Job Outputs')
      job.sendFailoverRequest()
      return
  else:
    gLogger.verbose('Job has no OutputData or OutputSandbox requirement')

  try:
    job.finalize(arguments)
  except Exception, x:
    message = 'JobWrapper failed the finalization phase with exception: \n '+str(x)
    gLogger.warn(message)
    return

###################### Note ##############################
# The below arguments are automatically generated by the #
# JobAgent, do not edit them.                            #
##########################################################
try:
  jobArgs = @JOBARGS@
  execute( jobArgs )
except:
  pass
