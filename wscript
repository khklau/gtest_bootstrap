import fnmatch
import hashlib
import os
import shutil
import stat
import subprocess
import tarfile
import urllib
import zipfile
from waflib import Logs
from waflib.extras.preparation import PreparationContext
from waflib.extras.build_status import BuildStatus
from waflib.extras.filesystem_utils import removeSubdir
from waflib.extras.mirror import MirroredZipFile

__downloadUrl = 'https://googletest.googlecode.com/files/%s'
__srcFile = 'gtest-1.7.0.zip'
__srcSha256Checksum = '\x24\x7c\xa1\x8d\xd8\x3f\x53\xde\xb1\x32\x8b\xe1\x7e\x4b\x1b\xe3\x15\x14\xce\xdf\xc1\xe3\x42\x4f\x67\x2b\xf1\x1f\xd7\xe0\xd6\x0d'
__srcDir = 'src'

def options(optCtx):
    optCtx.load('dep_resolver')

def prepare(prepCtx):
    prepCtx.options.dep_base_dir = prepCtx.srcnode.find_dir('..').abspath()
    prepCtx.load('dep_resolver')
    status = BuildStatus.init(prepCtx.path.abspath())
    if status.isSuccess():
	prepCtx.msg('Preparation already complete', 'skipping')
	return
    srcPath = os.path.join(prepCtx.path.abspath(), __srcDir)
    file = MirroredZipFile(
	    __srcSha256Checksum,
	    __downloadUrl % __srcFile,
	    os.path.join(prepCtx.path.abspath(), __srcFile))
    prepCtx.msg('Synchronising', file.getSrcUrl())
    if file.sync(10):
	prepCtx.msg('Saved to', file.getTgtPath())
    else:
	prepCtx.fatal('Synchronisation failed')
    extractDir = 'gtest-1.7.0'
    removeSubdir(prepCtx.path.abspath(), __srcDir, extractDir, 'bin', 'lib', 'include')
    prepCtx.start_msg('Extracting files to')
    file.extract(prepCtx.path.abspath())
    os.rename(extractDir, __srcDir)
    prepCtx.end_msg(srcPath)
    for dirPath, subDirList, fileList in os.walk(os.path.join(srcPath, 'scripts')):
	for file in fileList:
	    os.chmod(os.path.join(dirPath, file), stat.S_IXUSR | stat.S_IRUSR | stat.S_IWUSR)

def configure(confCtx):
    confCtx.load('dep_resolver')
    status = BuildStatus.init(confCtx.path.abspath())
    if status.isSuccess():
	confCtx.msg('Configuration already complete', 'skipping')
	return
    srcPath = os.path.join(confCtx.path.abspath(), __srcDir)
    os.chdir(srcPath)
    if os.name == 'posix':
	returnCode = subprocess.call([
		'sh',
		os.path.join(srcPath, 'configure'),
		'--prefix=%s' % confCtx.srcnode.abspath()])
	if returnCode != 0:
	    confCtx.fatal('Google Test configure failed: %d' % returnCode)
    elif os.name == 'nt':
	# Nothing to do, just use the provided VS solution
	return
    else:
	confCtx.fatal('Unsupported OS %s' % os.name)

def build(buildCtx):
    status = BuildStatus.load(buildCtx.path.abspath())
    if status.isSuccess():
	Logs.pprint('NORMAL', 'Build already complete                   :', sep='')
	Logs.pprint('GREEN', 'skipping')
	return
    srcPath = os.path.join(buildCtx.path.abspath(), __srcDir)
    os.chdir(srcPath)
    if os.name == 'posix':
	returnCode = subprocess.call([
		'make'])
    elif os.name == 'nt':
	returnCode = subprocess.call([
		'devenv.com',
		os.path.join(srcPath, 'msvc', 'gtest.sln')])
    else:
	confCtx.fatal('Unsupported OS %s' % os.name)
    if returnCode != 0:
	buildCtx.fatal('Google Test build failed: %d' % returnCode)
    libPath = os.path.join(buildCtx.path.abspath(), 'lib')
    os.mkdir(libPath)
    for dirPath, subDirList, fileList in os.walk(os.path.join(srcPath, 'lib')):
	for file in fileList:
	    if fnmatch.fnmatch(file, 'libgtest*'):
		filePath = os.path.join(dirPath, file)
		if os.path.islink(filePath):
		    linkTgt = os.readlink(filePath)
		    linkSrc = os.path.join(libPath, file)
		    if not os.path.exists(linkSrc):
			os.symlink(linkTgt, os.path.join(libPath, file))
		else:
		    shutil.copy2(os.path.join(dirPath, file), libPath)
    shutil.copytree(os.path.join(srcPath, 'include'), os.path.join(buildCtx.path.abspath(), 'include'))
    binPath = os.path.join(buildCtx.path.abspath(), 'bin')
    os.mkdir(binPath)
    configFile = os.path.join(srcPath, 'scripts', 'gtest-config')
    if os.access(configFile, os.R_OK):
	shutil.copy2(configFile, binPath)
    else:
	buildCtx.fatal('Google Test build failed: %s is missing' % configFile)
    status.setSuccess()
