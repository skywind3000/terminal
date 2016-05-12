#! /usr/bin/python
import sys, os, time
import subprocess


#----------------------------------------------------------------------
# configure
#----------------------------------------------------------------------
class configure (object):

	def __init__ (self):
		self.dirhome = os.path.abspath(os.path.dirname(__file__))
		self.diruser = os.path.abspath(os.path.expanduser('~'))
		self.unix = sys.platform[:3] != 'win' and True or False
		self.temp = os.environ.get('temp', os.environ.get('tmp', '/tmp'))
		self.tick = long(time.time()) % 100
		if self.unix:
			temp = os.environ.get('tmp', '/tmp')
			if not temp:
				temp = '/tmp'
			folder = os.path.join(temp, 'runner/folder')
			if not os.path.exists(folder):
				try:
					os.makedirs(folder, 0777)
				except:
					folder = ''
			if folder:
				self.temp = folder
				try:
					os.chmod(self.temp, 0777)
				except:
					pass
		self.temp = os.path.join(self.temp, 'winex_%02d.cmd'%self.tick)
		self.cygwin = ''
		self.GetShortPathName = None
	
	def call (self, args, stdin = None):
		p = subprocess.Popen(args, shell = False,
				stdin = subprocess.PIPE,
				stdout = subprocess.PIPE, 
				stderr = subprocess.PIPE)
		if stdin != None:
			p.stdin.write(stdin)
			p.stdin.flush()
		p.stdin.close()
		stdout = p.stdout.read()
		stderr = p.stderr.read()
		code = p.wait()
		return code, stdout, stderr

	def where (self, filename, path = []):
		PATH = os.environ.get('PATH', '')
		if sys.platform[:3] == 'win':
			PATH = PATH.split(';')
		else:
			PATH = PATH.split(':')
		if path:
			PATH.extend(path)
		for base in PATH:
			path = os.path.join(base, filename)
			if os.path.exists(path):
				return path
		return None
		
	def escape (self, path):
		path = path.replace('\\', '\\\\').replace('"', '\\"')
		return path.replace('\'', '\\\'')

	def darwin_osascript (self, script):
		for line in script:
			#print line
			pass
		if type(script) == type([]):
			script = '\n'.join(script)
		p = subprocess.Popen(['/usr/bin/osascript'], shell = False,
				stdin = subprocess.PIPE, stdout = subprocess.PIPE,
				stderr = subprocess.STDOUT)
		p.stdin.write(script)
		p.stdin.flush()
		p.stdin.close()
		text = p.stdout.read()
		p.stdout.close()
		code = p.wait() 
		#print text
		return code, text

	def darwin_open_system (self, title, script, profile = None):
		script = [ line for line in script ]
		script.insert(0, 'clear')
		fp = open(self.temp, 'w')
		fp.write('#! /bin/sh\n')
		for line in script:
			fp.write(line + '\n')
		fp.close()
		os.chmod(self.temp, 0777)
		cmd = self.where('open')
		self.call([cmd, '-a', 'Terminal', self.temp])
		return 0, ''

	def darwin_open_terminal (self, title, script, profile = None):
		osascript = []
		command = []
		for line in script:
			if line.rstrip('\r\n\t ') == '':
				continue
			line = line.replace('\\', '\\\\')
			line = line.replace('"', '\\"')
			line = line.replace("'", "\\'")
			command.append(line)
		command.insert(0, 'clear')
		command = '; '.join(command)
		osascript.append('tell application "Terminal"')
		osascript.append('  if it is running then')
		osascript.append('     do script "%s; exit"'%command)
		osascript.append('  else')
		osascript.append('     do script "%s; exit" in window 1'%command)
		osascript.append('  end if')
		x = '  set current settings of selected tab of '
		x += 'window 1 to settings set "%s"'
		if profile != None:
			osascript.append(x%profile)
		osascript.append('  activate')
		osascript.append('end tell')
		return self.darwin_osascript(osascript)

	def darwin_open_iterm (self, title, script, profile = None):
		osascript = []
		command = []
		script = [ line for line in script ]
		if profile:
			script.insert(0, 'clear')
			script.insert(0, 'echo "\033]50;SetProfile=%s\a"'%profile)
		for line in script:
			if line.rstrip('\r\n\t ') == '':
				continue
			line = line.replace('\\', '\\\\\\\\')
			line = line.replace('"', '\\\\\\"')
			line = line.replace("'", "\\\\\\'")
			command.append(line)
		command = '; '.join(command)
		osascript.append('tell application "iTerm"')
		osascript.append('set myterm to (make new terminal)')
		osascript.append('tell myterm')
		osascript.append('set mss to (make new session at the end of sessions)')
		osascript.append('tell mss')
		if title:
			osascript.append('     set name to "%s"'%self.escape(title))
		osascript.append('     activate')
		osascript.append('     exec command "/bin/bash -c \\"%s\\""'%command)
		osascript.append('end tell')
		osascript.append('end tell')
		osascript.append('end tell')
		return self.darwin_osascript(osascript)
	
	def unix_escape (self, argument, force = False):
		argument = argument.replace('\\', '\\\\')
		argument = argument.replace('"', '\\"')
		argument = argument.replace("'", "\\'")
		return argument.replace(' ', '\\ ')

	def win32_escape (self, argument, force = False):
		if force == False and argument:
			clear = True
			for n in ' \n\r\t\v\"':
				if n in argument:
					clear = False
					break
			if clear:
				return argument
		output = '"'
		size = len(argument)
		i = 0
		while True:
			blackslashes = 0
			while (i < size and argument[i] == '\\'):
				i += 1
				blackslashes += 1
			if i == size:
				output += '\\' * (blackslashes * 2)
				break
			if argument[i] == '"':
				output += '\\' * (blackslashes * 2 + 1)
				output += '"'
			else:
				output += '\\' * blackslashes
				output += argument[i]
			i += 1
		output += '"'
		return output

	def win32_path_short (self, path):
		path = os.path.abspath(path)
		if self.unix:
			return path
		if not self.GetShortPathName:
			self.kernel32 = None
			self.textdata = None
			try:
				import ctypes
				self.kernel32 = ctypes.windll.LoadLibrary("kernel32.dll")
				self.textdata = ctypes.create_string_buffer('\000' * 1024)
				self.GetShortPathName = self.kernel32.GetShortPathNameA
				args = [ ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int ]
				self.GetShortPathName.argtypes = args
				self.GetShortPathName.restype = ctypes.c_uint32
			except: pass
		if not self.GetShortPathName:
			return path
		retval = self.GetShortPathName(path, self.textdata, 1024)
		shortpath = self.textdata.value
		if retval <= 0:
			return ''
		return shortpath

	# start cmd.exe in a new window and execute script
	def win32_open_console (self, title, script, profile = None):
		fp = open(self.temp, 'w')
		fp.write('@echo off\n')
		if title:
			fp.write('title %s\n'%self.win32_escape(title))
		for line in script:
			fp.write(line + '\n')
		fp.close()
		fp = None
		pathname = self.win32_path_short(self.temp)
		os.system('start cmd /C %s'%(pathname))
		return 0
	
	def darwin_open_xterm (self, title, script, profile = None):
		command = []
		for line in script:
			if line.rstrip('\r\n\t ') == '':
				continue
			line = line.replace('\\', '\\\\')
			line = line.replace('"', '\\"')
			line = line.replace("'", "\\'")
			command.append(line)
		command = '; '.join(command)
		if title:
			command = 'xterm -T "%s" -e "%s" &'%(title, command)
		else:
			command = 'xterm -e "%s" &'%(command)
		subprocess.call(['/bin/sh', '-c', command])
		return 0

	def linux_open_xterm (self, title, script, profile = None):
		command = []
		for line in script:
			if line.rstrip('\r\n\t ') == '':
				continue
			line = line.replace('\\', '\\\\')
			line = line.replace('"', '\\"')
			line = line.replace("'", "\\'")
			command.append(line)
		command = '; '.join(command)
		cmdline = self.where('xterm') + ' '
		if title:
			title = self.escape(title)
			cmdline += '-T "%s" '%title
		cmdline += '-e "%s" '%command
		os.system(cmdline + ' & ')
		return 0

	def linux_open_gnome (self, title, script, profile = None):
		command = []
		for line in script:
			if line.rstrip('\r\n\t ') == '':
				continue
			line = line.replace('\\', '\\\\')
			line = line.replace('"', '\\"')
			line = line.replace("'", "\\'")
			command.append(line)
		command = '; '.join(command)
		command = '%s -c \"%s\"'%(self.where('bash'), command)
		cmdline = self.where('gnome-terminal') + ' '
		if title:
			title = self.escape(title and title or '')
			cmdline += '-t "%s" '%title
		if profile:
			cmdline += '--window-with-profile="%s" '%profile
		cmdline += ' --command=\'%s\''%command
		os.system(cmdline)
		return 0

	def cygwin_open_cmd (self, title, script, profile = None):
		temp = os.environ.get('TEMP', os.environ.get('TMP', '/tmp'))
		filename = os.path.split(self.temp)[-1]
		cwd = os.getcwd()
		fp = open(os.path.join(temp, filename), 'w')
		fp.write('@echo off\n')
		if title:
			fp.write('title %s\n'%self.win32_escape(title))
		for line in script:
			fp.write(line + '\n')
		fp.close()
		fp = None
		command = 'cygstart cmd /C %s'%(filename)
		# print script
		p = subprocess.Popen(['cygstart', 'cmd', '/C', filename], cwd = temp)
		p.wait()
		return 0

	def cygwin_write_script (self, filename, script):
		fp = open(filename, 'w')
		fp.write('#! /bin/sh\n')
		for line in script:
			fp.write('%s\n'%line)
		fp.close()
		fp = None
		return 0

	def cygwin_win_path (self, path):
		code, stdout, stderr = self.call(['cygpath', '-w', path])
		return stdout.strip('\r\n')

	def cygwin_open_bash (self, title, script, profile = None):
		filename = os.path.split(self.temp)[-1]
		scriptname = os.path.join('/tmp', filename)
		script = [ n for n in script ]
		script.insert(0, 'cd %s'%self.unix_escape(os.getcwd()))
		self.cygwin_write_script(scriptname, script)
		command = ['cygstart', 'bash']
		if profile == 'login':
			command.append('--login')
		self.call(command + ['-i', scriptname])
		return 0
	
	def cygwin_open_mintty (self, title, script, profile = None):
		filename = os.path.split(self.temp)[-1]
		scriptname = os.path.join('/tmp', filename)
		script = [ n for n in script ]
		script.insert(0, 'cd %s'%self.unix_escape(os.getcwd()))
		self.cygwin_write_script(scriptname, script)
		command = ['cygstart', 'mintty']
		# if  title:
			# command += ['-t', title]
		if os.path.exists('/Cygwin-Terminal.ico'):
			command += ['-i', '/Cygwin-Terminal.ico']
		command += ['-e', 'bash']
		if profile == 'login':
			command.append('--login')
		command.extend(['-i', scriptname])
		self.call(command)
		return 0

	# convert windows path to cygwin path
	def win2cyg (self, path):
		path = os.path.abspath(path)
		return '/cygdrive/%s%s'%(path[0], path[2:].replace('\\', '/'))

	# convert cygwin path to windows path
	def cyg2win (self, path):
		if path[1:2] == ':':
			return os.path.abspath(path)
		if path.lower().startswith('/cygdrive/'):
			path = path[10] + ':' + path[11:]
			return path
		if not path.startswith('/'):
			raise Exception('cannot convert path: %s'%path)
		if not self.cygwin:
			raise Exception('cannot find cygwin root')
		if sys.platform == 'cygwin':
			return self.cygwin_win_path(path)
		return os.path.abspath(os.path.join(self.cygwin, path[1:]))
	
	# use bash in cygwin to execute script and return output
	def win32_cygwin_execute (self, script, login = False):
		if not self.cygwin:
			return -1, None
		if not os.path.exists(self.cygwin):
			return -2, None
		if not os.path.exists(os.path.join(self.cygwin, 'bin/sh.exe')):
			return -3, None
		bash = os.path.join(self.cygwin, 'bin/bash')
		filename = os.path.split(self.temp)[-1]
		tempfile = os.path.join(self.cygwin, 'tmp/' + filename)
		fp = open(tempfile, 'wb')
		fp.write('#! /bin/sh\n')
		path = self.win2cyg(os.getcwd())
		fp.write('cd %s\n'%self.unix_escape(path))
		for line in script:
			fp.write('%s\n'%line)
		fp.close()
		command = [bash]
		if login:
			command.append('--login')
		command.extend(['-i', '/tmp/' + filename])
		p = subprocess.Popen(command, shell = False,
				stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
		text = p.stdout.read()
		p.stdout.close()
		code = p.wait()
		return code, text

	# use bash in cygwin to execute script and output to current cmd window
	def win32_cygwin_now (self, script, login = False):
		if not self.cygwin:
			return -1, None
		if not os.path.exists(self.cygwin):
			return -2, None
		if not os.path.exists(os.path.join(self.cygwin, 'bin/sh.exe')):
			return -3, None
		bash = os.path.join(self.cygwin, 'bin/bash')
		filename = os.path.split(self.temp)[-1]
		tempfile = os.path.join(self.cygwin, 'tmp/' + filename)
		fp = open(tempfile, 'wb')
		fp.write('#! /bin/sh\n')
		path = self.win2cyg(os.getcwd())
		fp.write('cd %s\n'%self.unix_escape(path))
		for line in script:
			fp.write('%s\n'%line)
		fp.close()
		command = [bash]
		if login:
			command.append('--login')
		command.extend(['-i', '/tmp/' + filename])
		subprocess.call(command, shell = False)
		return 0

	# open bash of cygwin in a new window and execute script
	def win32_cygwin_open_bash (self, title, script, profile = None):
		if not self.cygwin:
			return -1, None
		if not os.path.exists(self.cygwin):
			return -2, None
		if not os.path.exists(os.path.join(self.cygwin, 'bin/sh.exe')):
			return -3, None
		bash = os.path.join(self.cygwin, 'bin/bash.exe')
		filename = os.path.split(self.temp)[-1]
		tempfile = os.path.join(self.cygwin, 'tmp/' + filename)
		fp = open(tempfile, 'wb')
		fp.write('#! /bin/sh\n')
		path = self.win2cyg(os.getcwd())
		fp.write('cd %s\n'%self.unix_escape(path))
		for line in script:
			fp.write('%s\n'%line)
		fp.close()
		short_bash = self.win32_path_short(bash)
		command = 'start %s '%short_bash
		command += '--login -i /tmp/' + filename
		os.system(command)
		return 0

	# open mintty of cygwin in a new window and execute script
	def win32_cygwin_open_mintty (self, title, script, profile = None):
		if not self.cygwin:
			return -1, None
		if not os.path.exists(self.cygwin):
			return -2, None
		if not os.path.exists(os.path.join(self.cygwin, 'bin/sh.exe')):
			return -3, None
		mintty = os.path.join(self.cygwin, 'bin/mintty.exe')
		filename = os.path.split(self.temp)[-1]
		tempfile = os.path.join(self.cygwin, 'tmp/' + filename)
		fp = open(tempfile, 'wb')
		fp.write('#! /bin/sh\n')
		path = self.win2cyg(os.getcwd())
		fp.write('cd %s\n'%self.unix_escape(path))
		for line in script:
			fp.write('%s\n'%line)
		fp.close()
		shortname = self.win32_path_short(mintty)
		command = 'start %s '%shortname
		if os.path.exists(os.path.join(self.cygwin, 'Cygwin-Terminal.ico')):
			command += '-i /Cygwin-Terminal.ico '
		if title:
			command += '-t "%s" '%title
		command += '-e /usr/bin/bash '
		if profile == 'login' or True:
			command += '--login '
		command += '-i /tmp/' + filename
		# print command
		os.system(command)
		return 0


#----------------------------------------------------------------------
# die
#----------------------------------------------------------------------
def die(message):
	sys.stderr.write('%s\n'%message)
	sys.stderr.flush()
	sys.exit(0)
	return 0



#----------------------------------------------------------------------
# terminal class
#----------------------------------------------------------------------
class Terminal (object):

	def __init__ (self):
		self.config = configure()
		self.unix = sys.platform[:3] != 'win' and True or False
		self.cygwin_login = False
		self.post_command = ''
	
	def __win32_open_terminal (self, terminal, title, script, profile):
		if terminal in ('', 'system', 'dos', 'win', 'windows', 'command', 'cmd'):
			self.config.win32_open_console(title, script)
		elif terminal in ('cygwin', 'bash', 'mintty', 'cygwin-mintty', 'cygwinx'):
			if not self.config.cygwin:
				die('please give cygwin path in profile')
				return -1
			if not os.path.exists(self.config.cygwin):
				die('can not find cygwin in: %s'%self.config.cygwin)
				return -2
			if not os.path.exists(os.path.join(self.config.cygwin, 'bin/sh.exe')):
				die('can not verify cygwin in: %s'%self.config.cygwin)
				return -3
			if terminal in ('cygwin', 'bash'):
				self.config.win32_cygwin_open_bash(title, script, profile)
			elif terminal in ('cygwin-silent', 'cygwin-shell', 'cygwinx'):
				self.config.win32_cygwin_now(script, True)
			else:
				self.config.win32_cygwin_open_mintty(title, script, profile)
		else:
			die('bad terminal name: %s'%terminal)
			return -4
		return 0

	def __cygwin_open_terminal (self, terminal, title, script, profile):
		if terminal in ('dos', 'win', 'cmd', 'command', 'system', 'windows'):
			self.config.cygwin_open_cmd(title, script, profile)
		elif terminal in ('bash', 'sh', '', 'default'):
			self.config.cygwin_open_bash(title, script, profile)
		elif terminal in ('mintty', 'cygwin-mintty'):
			if not title:
				title = 'Cygwin Mintty'
			self.config.cygwin_open_mintty(title, script, profile)
		else:
			die('bad terminal name: %s'%terminal)
			return -1
		return 0

	def __darwin_open_terminal (self, terminal, title, script, profile):
		if terminal in ('', 'system', 'default'):
			if (not profile) and (not title):
				self.config.darwin_open_system(title, script, profile)
			else:
				self.config.darwin_open_terminal(title, script, profile)
		elif terminal in ('terminal',):
			self.config.darwin_open_terminal(title, script, profile)
		elif terminal in ('iterm', 'iterm2'):
			self.config.darwin_open_iterm(title, script, profile)
		elif terminal in ('xterm', 'x'):
			self.config.darwin_open_xterm(title, script, profile)
		else:
			die('bad terminal name: %s'%terminal)
			return -1
		return 0

	def __linux_open_terminal (self, terminal, title, script, profile):
		if terminal in ('xterm', '', 'default', 'system', 'x'):
			self.config.linux_open_xterm(title, script, profile)
		elif terminal in ('gnome', 'gnome-terminal'):
			self.config.linux_open_gnome(title, script, profile)
		else:
			die('bad terminal name: %s'%terminal)
			return -1
		return 0

	def open_terminal (self, terminal, title, script, profile):
		if terminal == None:
			terminal = ''
		if sys.platform[:3] == 'win':
			if script == None:
				return ('cmd (default)', 'cygwin', 'mintty', 'cygwinx')
			return self.__win32_open_terminal(terminal, title, script, profile)
		elif sys.platform == 'cygwin':
			if script == None:
				return ('bash (default)', 'mintty', 'windows')
			return self.__cygwin_open_terminal(terminal, title, script, profile)
		elif sys.platform == 'darwin':
			if script == None:
				return ('terminal (default)', 'iterm')
			return self.__darwin_open_terminal(terminal, title, script, profile)
		else:
			if script == None:
				return ('xterm (default)', 'gnome-terminal')
			return self.__linux_open_terminal(terminal, title, script, profile)
		return 0

	def check_windows (self, terminal):
		if sys.platform[:3] == 'win':
			if terminal == None:
				return True
			if terminal in ('', 'system', 'dos', 'win', 'windows', 'command', 'cmd'):
				return True
		elif sys.platform == 'cygwin':
			if terminal in ('dos', 'win', 'cmd', 'command', 'system', 'windows'):
				return True
		return False
	
	def execute (self, terminal, title, script, cwd, wait, profile):
		lines = [ line for line in script ]
		windows = self.check_windows(terminal)
		script = []
		if cwd == None:
			cwd = os.getcwd()
		if terminal == None:
			terminal = ''
		if sys.platform[:3] == 'win' and cwd[1:2] == ':':
			if terminal in ('', 'system', 'dos', 'win', 'windows', 'command', 'cmd'):
				script.append(cwd[:2])
				script.append('cd "%s"'%cwd)
			else:
				script.append('cd "%s"'%self.config.win2cyg(cwd))
		elif sys.platform == 'cygwin':
			if terminal in ('dos', 'win', 'cmd', 'command', 'system', 'windows'):
				path = self.config.cyg2win(os.path.abspath(cwd))
				script.append(path[:2])
				script.append('cd "%s"'%path)
			else:
				script.append('cd "%s"'%cwd)
		else:
			script.append('cd "%s"'%cwd)
		script.extend(lines)
		if wait:
			if windows:
				script.append('pause')
			else:
				script.append('read -n1 -rsp "press any key to confinue ..."')
		if self.post_command:
			script.append(self.post_command)
		return self.open_terminal(terminal, title, script, profile)

	def run_command (self, terminal, title, command, cwd, wait, profile):
		script = [ command ]
		return self.execute(terminal, title, script, cwd, wait, profile)

	def run_tee (self, command, teename, shell = False, wait = False):
		args = []
		for n in command:
			if sys.platform[:3] == 'win':
				n = self.config.win32_escape(n)
			else:
				n = self.config.unix_escape(n)
			args.append(n)
		import subprocess
		p = subprocess.Popen(args, stdin = None, stdout = subprocess.PIPE, \
				stderr = subprocess.STDOUT, shell = shell)
		if sys.platform[:3] != 'win' and '~' in teename:
			teename = os.path.expanduser(teename)
		f = open(teename, 'w')
		while True:
			text = p.stdout.readline()
			if text in ('', None):
				break
			f.write(text)
			f.flush()
			sys.stdout.write(text)
			sys.stdout.flush()
		p.stdout.close()
		p.wait()
		f.close()
		if wait:
			if sys.platform[:3] == 'win':
				os.system('pause')
			else:
				os.system('read -n1 -rsp "press any key to continue ..."')
		return 0



#----------------------------------------------------------------------
# main routine
#----------------------------------------------------------------------
def main(argv = None, shellscript = None):
	if argv == None:
		argv = sys.argv
	argv = [ n for n in argv ]
	args = []
	cmds = []
	skip = ['-h', '--help', '-w', '-s']
	index = 1
	stdin = False
	if len(argv) > 0:
		args.append(argv[0])
	while index < len(argv):
		data = argv[index]
		if data in ('-s', '--stdin'):
			stdin = True
		if data[:2] == '--':
			args.append(data)
			index += 1
		elif data in skip:
			args.append(data)
			index += 1
		elif data[:1] == '-':
			args.append(data)
			index += 1
			if index >= len(argv):
				break
			args.append(argv[index])
			index += 1
		else:
			cmds = argv[index:]
			break
	terminal = Terminal()
	help = terminal.open_terminal('', '', None, '')
	text = 'available terminal: ' 
	text += ', '.join(help)
	import optparse
	if len(cmds) == 0 and len(args) > 0 and stdin == False:
		args.append('--help')
	elif stdin and len(cmds) > 0 and len(args) > 1:
		args.append('--help')
	desc = 'Execute program in a new terminal window'
	parser = optparse.OptionParser( \
			usage = 'usage: %prog [options] command [args ...]',
			version = '0.0.0',
			description = desc)
	parser.add_option('-t', '--title', dest = 'title', default = None,
			help = 'title of new window')
	parser.add_option('-m', '--terminal', dest = 'terminal', default = None, 
			help = text)
	parser.add_option('-p', '--profile', dest = 'profile', default = None,
			help = 'terminal profile')
	parser.add_option('-d', '--cwd', dest = 'cwd', default = '',
			help = 'working directory')
	parser.add_option('-w', '--wait', dest = 'wait', default = False,
			action = 'store_true', help = 'wait before exit')
	parser.add_option('-o', '--post', dest = 'post', default = '',
			help = 'post action')
	parser.add_option('-s', '--stdin', dest = 'stdin', default = False,
			action = 'store_true', help = 'read commands from stdin')
	parser.add_option('-e', '--tee', dest = 'tee', default = '',
			help = 'redirect output to file')
	if sys.platform[:3] == 'win':
		parser.add_option('-c', '--cygwin', dest = 'cygwin', default = '',
				help = 'cygwin home path when using cygwin terminal')
	opts, _ = parser.parse_args(args)
	if not opts.cwd:
		opts.cwd = os.getcwd()
	command = []
	if sys.platform[:3] == 'win':
		cygwin = opts.cygwin
		terminal.config.cygwin = cygwin
	if shellscript:
		script = [ line for line in shellscript ]
		if opts.post:
			terminal.post_command = opts.post
		terminal.execute(opts.terminal, opts.title, script,
				opts.cwd, opts.wait, opts.profile)
	elif opts.stdin:
		text = ''
		while True:
			hr = sys.stdin.read()
			if hr == '': break
			text += hr
		script = text.split('\n')
		if opts.post:
			terminal.post_command = opts.post
		terminal.execute(opts.terminal, opts.title, script,
				opts.cwd, opts.wait, opts.profile)
	elif opts.tee != '':
		shell = False
		if sys.platform[:3] == 'win':
			shell = True
		terminal.run_tee(cmds, opts.tee, shell, opts.wait)
	else:
		for n in cmds:
			if terminal.check_windows(opts.terminal):
				n = terminal.config.win32_escape(n)
			else:
				n = terminal.config.unix_escape(n)
			command.append(n)
		command = ' '.join(command)
		if opts.post:
			terminal.post_command = opts.post
		terminal.run_command(opts.terminal, opts.title, command, 
			opts.cwd, opts.wait, opts.profile)
	return 0


#----------------------------------------------------------------------
# run clever for vimmake
#----------------------------------------------------------------------
def vimtool():
	
	return 0


#----------------------------------------------------------------------
# testing casen
#----------------------------------------------------------------------
if __name__ == '__main__':
	def test1():
		cfg = configure()
		cfg.darwin_open_terminal('111', ['ls -la /', 'read -n1 -rsp press\\ any\\ key\\ to\\ continue\\ ...', 'echo "fuck you"'])

	def test2():
		args = [ 'terminal', '-h' ]
		#args = [ 'terminal', '-w', '--terminal=cmd', '--cwd=e:/lesson', '--cygwin=d:/linux', '--title=fuck', 'DIR']
		main(args)
		return 0

	def test3():
		args = [ 'terminal', '-w', '--terminal=cmd', '--stdin' ]
		main(args)
		return 0
	
	#test2()
	main()



