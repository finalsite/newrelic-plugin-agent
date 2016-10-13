import os, sys, types
from subprocess import Popen, PIPE

class ImportWrapper(object):
  def __init__(self, wrapped):
    self.wrapped = wrapped

  def __getattr__(self, name):
    try:
      return getattr(self.wrapped, name)
    except AttributeError:
      def fn(*args, **kwargs):
        return Command(name).run(*args, **kwargs)
      
      fn.__doc__ = '`%s` command' % name
      fn.__name__ = name
      setattr(self.wrapped, name, fn)
      
    return fn

class CommandStatus(object):
  def __init__(self):
    self._output = ''
    self._error  = ''
    self._code   = 0
  
  def __repr__(self):
    return '<{0}:{1} code="{2}" output="{3}" error="{4}">'.format(
      type(self).__name__, hex(id(self)), self._code, self._output, self._error
    )
    
  @property 
  def output(self):
    return self._output
  
  @output.setter
  def output(self, value):
    self._output = value
    
  @property 
  def error(self):
    return self._error
    
  @error.setter
  def error(self, value):
    self._error = value

  @property
  def code(self):
    return self._code
    
  @code.setter
  def code(self, value):
    self._code = value

class Command(object):
  def __init__(self, name):
    self._path = self.__class__.which(name)
    
  @classmethod
  def which(cls, name):
    def is_executable_file(fpath):
      return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(name)
    if fpath:
      if is_executable_file(name): return name
    else:
      for path in os.environ['PATH'].split(os.pathsep):
        fpath = os.path.join(path.strip('"'), name)
        if is_executable_file(fpath): return fpath
    
    return None
  
  def run(self, *args, **kwargs):
    # unshift command into list
    args = [self._path] + list(args)
    
    # add keyword arguments to command arguments
    for (opt, arg) in kwargs.items():
      if len(opt) > 1:
        args.append('--%s' % opt)
      else:
        args.append('-%s' % opt)
      args.append(arg)

    status = CommandStatus()
    process = Popen(args, stdout=PIPE, stderr=PIPE)

    status.output, status.error = process.communicate()
    status.code = process.returncode
    
    return status
    
sys.modules[__name__] = ImportWrapper(sys.modules[__name__])
