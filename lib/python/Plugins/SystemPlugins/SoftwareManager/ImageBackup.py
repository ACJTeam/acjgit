from enigma import getEnigmaVersionString
from Screens.Screen import Screen
from Components.Button import Button
from Components.SystemInfo import SystemInfo
from Components.Label import Label
from Components.ActionMap import ActionMap
from Components.About import about
from Components import Harddisk
from Screens.Console import Console
from Screens.MessageBox import MessageBox
from time import time, strftime, localtime
from os import path, system, makedirs, listdir, walk, statvfs
import commands
import datetime
from boxbranding import getBoxType, getMachineBrand, getMachineName, getDriverDate, getImageVersion, getImageBuild, getBrandOEM, getMachineBuild, getImageFolder, getMachineUBINIZE, getMachineMKUBIFS, getMachineMtdKernel, getMachineMtdRoot, getMachineKernelFile, getMachineRootFile, getImageFileSystem

VERSION = "Version 1.0 OpenACJ"

HaveGZkernel = True
if getMachineBuild() in ("vusolo4k", "spark", "spark7162", "hd51", "hd52", "gb7252"):
	HaveGZkernel = False

def Freespace(dev):
	statdev = statvfs(dev)
	space = (statdev.f_bavail * statdev.f_frsize) / 1024
	print "[ImageBackup] Free space on %s = %i kilobytes" %(dev, space)
	return space

class ImageBackup(Screen):
	skin = """
	<screen position="center,center" size="560,400" title="Image Backup">
		<ePixmap position="0,360"   zPosition="1" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
		<ePixmap position="140,360" zPosition="1" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
		<ePixmap position="280,360" zPosition="1" size="140,40" pixmap="skin_default/buttons/yellow.png" transparent="1" alphatest="on" />
		<ePixmap position="420,360" zPosition="1" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on" />
		<widget name="key_red" position="0,360" zPosition="2" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		<widget name="key_green" position="140,360" zPosition="2" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		<widget name="key_yellow" position="280,360" zPosition="2" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		<widget name="key_blue" position="420,360" zPosition="2" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		<widget name="info-hdd" position="10,30" zPosition="1" size="450,100" font="Regular;20" halign="left" valign="top" transparent="1" />
		<widget name="info-multi" position="10,80" zPosition="1" size="450,100" font="Regular;20" halign="left" valign="top" transparent="1" />
		<widget name="info-usb" position="10,150" zPosition="1" size="450,200" font="Regular;20" halign="left" valign="top" transparent="1" />
	</screen>"""

	def __init__(self, session, args = 0):
		Screen.__init__(self, session)
		self.session = session
		self.selection = 0
		self.list = self.list_files("/boot")
		self.MODEL = getBoxType()
		self.OEM = getBrandOEM()
		self.MACHINEBUILD = getMachineBuild()
		self.MACHINENAME = getMachineName()
		self.MACHINEBRAND = getMachineBrand()
		self.IMAGEFOLDER = getImageFolder()
		self.UBINIZE_ARGS = getMachineUBINIZE()
		self.MKUBIFS_ARGS = getMachineMKUBIFS()
		self.MTDKERNEL = getMachineMtdKernel()
		self.MTDROOTFS = getMachineMtdRoot()
		self.ROOTFSBIN = getMachineRootFile()
		self.KERNELBIN = getMachineKernelFile()
		self.ROOTFSTYPE = getImageFileSystem()
		print "[ImageBackup] BOX MACHINEBUILD = >%s<" %self.MACHINEBUILD
		print "[ImageBackup] BOX MACHINENAME = >%s<" %self.MACHINENAME
		print "[ImageBackup] BOX MACHINEBRAND = >%s<" %self.MACHINEBRAND
		print "[ImageBackup] BOX MODEL = >%s<" %self.MODEL
		print "[ImageBackup] OEM MODEL = >%s<" %self.OEM
		print "[ImageBackup] IMAGEFOLDER = >%s<" %self.IMAGEFOLDER
		print "[ImageBackup] UBINIZE = >%s<" %self.UBINIZE_ARGS
		print "[ImageBackup] MKUBIFS = >%s<" %self.MKUBIFS_ARGS
		print "[ImageBackup] MTDKERNEL = >%s<" %self.MTDKERNEL
		print "[ImageBackup] MTDROOTFS = >%s<" %self.MTDROOTFS
		print "[ImageBackup] ROOTFSTYPE = >%s<" %self.ROOTFSTYPE

		self["key_green"] = Button("USB")
		self["key_red"] = Button("HDD")
		self["key_blue"] = Button(_("Exit"))
		if SystemInfo["HasMultiBootGB"]:
			self["key_yellow"] = Button(_("STARTUP"))
			self["info-multi"] = Label(_("You can select with yellow the OnlineFlash Image\n or select Recovery to create a USB Disk Image for clean Install."))
			self.read_current_multiboot()
		else:
			self["key_yellow"] = Button("")
			self["info-multi"] = Label(" ")
		self["info-usb"] = Label(_("USB = Do you want to create a fullbackup on USB?\nThis will take between 4 and 15 minutes depending on the used filesystem and is fully automatic.\nMake sure you first insert an USB flash drive before you select USB."))
		self["info-hdd"] = Label(_("HDD = Do you want to create a fullbackup on HDD? \nThis only takes 2 or 10 minutes and is fully automatic."))
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
		{
			"blue": self.quit,
			"yellow": self.yellow,
			"green": self.green,
			"red": self.red,
			"cancel": self.quit,
		}, -2)

	def check_hdd(self):
		if not path.exists("/media/hdd"):
			self.session.open(MessageBox, _("No /hdd found !!\nPlease make sure you have a HDD mounted.\n"), type = MessageBox.TYPE_ERROR)
			return False
		if Freespace('/media/hdd') < 300000:
			self.session.open(MessageBox, _("Not enough free space on /hdd !!\nYou need at least 300Mb free space.\n"), type = MessageBox.TYPE_ERROR)
			return False
		return True

	def check_usb(self, dev):
		if Freespace(dev) < 300000:
			self.session.open(MessageBox, _("Not enough free space on %s !!\nYou need at least 300Mb free space.\n" % dev), type = MessageBox.TYPE_ERROR)
			return False
		return True

	def quit(self):
		self.close()

	def red(self):
		if self.check_hdd():
			self.doFullBackup("/hdd")

	def green(self):
		USB_DEVICE = self.SearchUSBcanidate()
		if USB_DEVICE == 'XX':
			text = _("No USB-Device found for fullbackup !!\n\n\n")
			text += _("To back-up directly to the USB-stick, the USB-stick MUST\n")
			text += _("contain a file with the name: \n\n")
			text += _("backupstick or backupstick.txt")
			self.session.open(MessageBox, text, type = MessageBox.TYPE_ERROR)
		else:
			if self.check_usb(USB_DEVICE):
				self.doFullBackup(USB_DEVICE)

	def yellow(self):
		if SystemInfo["HasMultiBootGB"]:
			self.selection = self.selection + 1
			if self.selection == len(self.list):
				self.selection = 0
			self["key_yellow"].setText(_(self.list[self.selection]))
			self.read_current_multiboot()

	def read_current_multiboot(self):
		if self.MACHINEBUILD in ("hd51","vs1500","h7"):
			if self.list[self.selection] == "Recovery":
				cmdline = self.read_startup("/boot/STARTUP").split("=",3)[3].split(" ",1)[0]
			else:
				cmdline = self.read_startup("/boot/" + self.list[self.selection]).split("=",3)[3].split(" ",1)[0]
		elif self.MACHINEBUILD in ("8100s"):
			if self.list[self.selection] == "Recovery":
				cmdline = self.read_startup("/boot/STARTUP").split("=",4)[4].split(" ",1)[0]
			else:
				cmdline = self.read_startup("/boot/" + self.list[self.selection]).split("=",4)[4].split(" ",1)[0]
		else:
			if self.list[self.selection] == "Recovery":
				cmdline = self.read_startup("/boot/cmdline.txt").split("=",1)[1].split(" ",1)[0]
			else:
				cmdline = self.read_startup("/boot/" + self.list[self.selection]).split("=",1)[1].split(" ",1)[0]
		cmdline = cmdline.lstrip("/dev/")
		self.MTDROOTFS = cmdline
		self.MTDKERNEL = cmdline[:-1] + str(int(cmdline[-1:]) -1)
		print "[ImageBackup] Multiboot rootfs ", self.MTDROOTFS
		print "[ImageBackup] Multiboot kernel ", self.MTDKERNEL

	def read_startup(self, FILE):
		self.file = FILE
		with open(self.file, 'r') as myfile:
			data=myfile.read().replace('\n', '')
		myfile.close()
		return data

	def list_files(self, PATH):
		files = []
		if SystemInfo["HasMultiBootGB"]:
			self.path = PATH
			for name in listdir(self.path):
				if path.isfile(path.join(self.path, name)):
					cmdline = self.read_startup("/boot/" + name).split("=",1)[1].split(" ",1)[0]
					if cmdline in Harddisk.getextdevices("ext4"):
						files.append(name)
			files.append("Recovery")
		return files

	def SearchUSBcanidate(self):
		for paths, subdirs, files in walk("/media"):
			for dir in subdirs:
				if not dir == 'hdd' and not dir == 'net':
					for file in listdir("/media/" + dir):
						if file.find("backupstick") > -1:
							print "[ImageBackup] USB-DEVICE found on: /media/%s" % dir
							return "/media/" + dir
			break
		return "XX"

	def doFullBackup(self, DIRECTORY):
		self.DIRECTORY = DIRECTORY
		self.TITLE = _("Fullbackup on %s") % (self.DIRECTORY)
		self.START = time()
		self.DATE = strftime("%Y%m%d_%H%M", localtime(self.START))
		self.IMAGEVERSION = self.imageInfo()
		if "ubi" in self.ROOTFSTYPE.split():
			self.MKFS = "/usr/sbin/mkfs.ubifs"
		elif "tar.bz2" in self.ROOTFSTYPE.split() or SystemInfo["HasMultiBootGB"]:
			self.MKFS = "/bin/tar"
			self.BZIP2 = "/usr/bin/bzip2"
		else:
			self.MKFS = "/usr/sbin/mkfs.jffs2"
		self.UBINIZE = "/usr/sbin/ubinize"
		self.NANDDUMP = "/usr/sbin/nanddump"
		self.WORKDIR= "%s/bi" %self.DIRECTORY
		self.TARGET="XX"

		## TESTING IF ALL THE TOOLS FOR THE BUILDING PROCESS ARE PRESENT
		if not path.exists(self.MKFS):
			text = "%s not found !!" %self.MKFS
			self.session.open(MessageBox, _(text), type = MessageBox.TYPE_ERROR)
			return
		if not path.exists(self.NANDDUMP):
			text = "%s not found !!" %self.NANDDUMP
			self.session.open(MessageBox, _(text), type = MessageBox.TYPE_ERROR)
			return

		self.SHOWNAME = "%s %s" %(self.MACHINEBRAND, self.MODEL)
		self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
		self.MAINDEST = "%s/%s" %(self.DIRECTORY,self.IMAGEFOLDER)
		self.EXTRA = "%s/fullbackup_%s/%s/%s" % (self.DIRECTORY, self.MODEL, self.DATE, self.IMAGEFOLDER)
		self.EXTRAOLD = "%s/fullbackup_%s/%s/%s" % (self.DIRECTORY, self.MODEL, self.DATE, self.MODEL)
		print "[ImageBackup] SHOWNAME: ", self.SHOWNAME
		print "[ImageBackup] MAINDESTOLD: ", self.MAINDESTOLD
		print "[ImageBackup] EXTRA: ", self.EXTRA
		print "[ImageBackup] EXTRAOLD: ", self.EXTRAOLD

		self.message = "echo -e '\n"
		self.message += (_("Fullback for %s\n" %self.SHOWNAME)).upper()
		self.message += VERSION + '\n'
		self.message += "____________________________________________________\n"
		self.message += _("Please be patient, a fullbackup will now be created.\n")
		if self.ROOTFSTYPE == "ubi":
			self.message += _("Due to the used filesystem, the fullbackup\n")
			self.message += _("will take about 3-12 minutes for this system.\n")
		elif SystemInfo["HasMultiBoot"] and self.list[self.selection] == "Recovery":
			self.message += _("because of the used filesystem the backup\n")
			self.message += _("will take about 30 minutes for this system.\n")
		elif "tar.bz2" in self.ROOTFSTYPE.split() or SystemInfo["HasMultiBootGB"]:
			self.message += _("because of the used filesystem the backup\n")
			self.message += _("will take about 1-4 minutes for this system.\n")
		else:
			self.message += _("This will take about 2-9 minutes for this system.\n")
		self.message += "____________________________________________________\n"
		self.message += "'"

		## PREPARING THE BUILDING ENVIRONMENT
		system("rm -rf %s" %self.WORKDIR)
		if not path.exists(self.WORKDIR):
			makedirs(self.WORKDIR)
		if not path.exists("/tmp/bi/root"):
			makedirs("/tmp/bi/root")
		system("sync")
		if SystemInfo["HasMultiBootGB"]:
			system("mount /dev/%s /tmp/bi/root" %self.MTDROOTFS)
		else:
			system("mount --bind / /tmp/bi/root")

		if "jffs2" in self.ROOTFSTYPE.split():
			cmd1 = "%s --root=/tmp/bi/root --faketime --output=%s/root.jffs2 %s" % (self.MKFS, self.WORKDIR, self.MKUBIFS_ARGS)
			cmd2 = None
			cmd3 = None
			print "[ImageBackup] jffs2 cmd1: ", cmd1
			print "[ImageBackup] jffs2 cmd2: ", cmd2
			print "[ImageBackup] jffs2 cmd3: ", cmd3
		elif "tar.bz2" in self.ROOTFSTYPE.split() or SystemInfo["HasMultiBootGB"]:
			cmd1 = "%s -cf %s/rootfs.tar -C /tmp/bi/root --exclude=/var/nmbd/* ." % (self.MKFS, self.WORKDIR)
			cmd2 = "%s %s/rootfs.tar" % (self.BZIP2, self.WORKDIR)
			cmd3 = None
			print "[ImageBackup] tar.bz2 cmd1: ", cmd1
			print "[ImageBackup] tar.bz2 cmd2: ", cmd2
			print "[ImageBackup] tar.bz2 cmd3: ", cmd3
		else:
			f = open("%s/ubinize.cfg" %self.WORKDIR, "w")
			f.write("[ubifs]\n")
			f.write("mode=ubi\n")
			f.write("image=%s/root.ubi\n" %self.WORKDIR)
			f.write("vol_id=0\n")
			f.write("vol_type=dynamic\n")
			f.write("vol_name=rootfs\n")
			f.write("vol_flags=autoresize\n")
			f.close()
			ff = open("%s/root.ubi" %self.WORKDIR, "w")
			ff.close()
			cmd1 = "%s -r /tmp/bi/root -o %s/root.ubi %s" % (self.MKFS, self.WORKDIR, self.MKUBIFS_ARGS)
			cmd2 = "%s -o %s/root.ubifs %s %s/ubinize.cfg" % (self.UBINIZE, self.WORKDIR, self.UBINIZE_ARGS, self.WORKDIR)
			cmd3 = "mv %s/root.ubifs %s/root.%s" %(self.WORKDIR, self.WORKDIR, self.ROOTFSTYPE)
			print "[ImageBackup] ubifs cmd1: ", cmd1
			print "[ImageBackup] ubifs cmd2: ", cmd2
			print "[ImageBackup] ubifs cmd3: ", cmd3

		cmdlist = []
		cmdlist.append(self.message)
		cmdlist.append('echo "Create: rootfs dump %s\n"' %self.ROOTFSTYPE)
		cmdlist.append(cmd1)
		if cmd2:
			cmdlist.append(cmd2)
		if cmd3:
			cmdlist.append(cmd3)

		if self.ROOTFSBIN == "rootfs.tar.bz2":
			cmdlist.append("chmod 644 %s/rootfs.%s" %(self.WORKDIR, self.ROOTFSTYPE))
		else:
			cmdlist.append("chmod 644 %s/root.%s" %(self.WORKDIR, self.ROOTFSTYPE))

		if self.MODEL in ("gbquad4k","gbue4k"):
			cmdlist.append('echo " "')
			cmdlist.append('echo "Create: boot dump boot.bin"')
			cmdlist.append('echo " "')
			cmdlist.append("dd if=/dev/mmcblk0p1 of=%s/boot.bin" % self.WORKDIR)
			cmdlist.append('echo " "')
			cmdlist.append('echo "Create: rescue dump rescue.bin"')
			cmdlist.append('echo " "')
			cmdlist.append("dd if=/dev/mmcblk0p3 of=%s/rescue.bin" % self.WORKDIR)

		cmdlist.append('echo " "')
		cmdlist.append('echo "Create: kernel dump"')
		cmdlist.append('echo " "')
		if SystemInfo["HasMultiBootGB"]:
			cmdlist.append("dd if=/dev/%s of=%s/kernel.bin" % (self.MTDKERNEL ,self.WORKDIR))
		elif self.MTDKERNEL == "mmcblk0p1" or self.MTDKERNEL == "mmcblk0p3":
			cmdlist.append("dd if=/dev/%s of=%s/%s" % (self.MTDKERNEL ,self.WORKDIR, self.KERNELBIN))
		else:
			cmdlist.append("nanddump -a -f %s/vmlinux.gz /dev/%s" % (self.WORKDIR, self.MTDKERNEL))
		cmdlist.append('echo " "')

		if HaveGZkernel:
			cmdlist.append('echo "Check: kerneldump"')
		cmdlist.append("sync")

		if SystemInfo["HasMultiBoot"] and self.list[self.selection] == "Recovery":
			GPT_OFFSET=0
			GPT_SIZE=1024
			BOOT_PARTITION_OFFSET = int(GPT_OFFSET) + int(GPT_SIZE)
			BOOT_PARTITION_SIZE=3072
			KERNEL_PARTITION_OFFSET = int(BOOT_PARTITION_OFFSET) + int(BOOT_PARTITION_SIZE)
			KERNEL_PARTITION_SIZE=8192
			ROOTFS_PARTITION_OFFSET = int(KERNEL_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
			ROOTFS_PARTITION_SIZE=819200
			SECOND_KERNEL_PARTITION_OFFSET = int(ROOTFS_PARTITION_OFFSET) + int(ROOTFS_PARTITION_SIZE)
			SECOND_ROOTFS_PARTITION_OFFSET = int(SECOND_KERNEL_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
			THRID_KERNEL_PARTITION_OFFSET = int(SECOND_ROOTFS_PARTITION_OFFSET) + int(ROOTFS_PARTITION_SIZE)
			THRID_ROOTFS_PARTITION_OFFSET = int(THRID_KERNEL_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
			FOURTH_KERNEL_PARTITION_OFFSET = int(THRID_ROOTFS_PARTITION_OFFSET) + int(ROOTFS_PARTITION_SIZE)
			FOURTH_ROOTFS_PARTITION_OFFSET = int(FOURTH_KERNEL_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
			SWAP_PARTITION_OFFSET = int(FOURTH_ROOTFS_PARTITION_OFFSET) + int(ROOTFS_PARTITION_SIZE)
			EMMC_IMAGE = "%s/disk.img"%self.WORKDIR
			EMMC_IMAGE_SIZE=3817472
			IMAGE_ROOTFS_SIZE=196608
			cmdlist.append('echo " "')
			cmdlist.append('echo "Create: Recovery Fullbackup disk.img"')
			cmdlist.append('echo " "')
			cmdlist.append('dd if=/dev/zero of=%s bs=1024 count=0 seek=%s' % (EMMC_IMAGE, EMMC_IMAGE_SIZE))
			cmdlist.append('parted -s %s mklabel gpt' %EMMC_IMAGE)
			PARTED_END_BOOT = int(BOOT_PARTITION_OFFSET) + int(BOOT_PARTITION_SIZE)
			cmdlist.append('parted -s %s unit KiB mkpart boot fat16 %s %s' % (EMMC_IMAGE, BOOT_PARTITION_OFFSET, PARTED_END_BOOT ))
			PARTED_END_KERNEL1 = int(KERNEL_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
			cmdlist.append('parted -s %s unit KiB mkpart kernel1 %s %s' % (EMMC_IMAGE, KERNEL_PARTITION_OFFSET, PARTED_END_KERNEL1 ))
			PARTED_END_ROOTFS1 = int(ROOTFS_PARTITION_OFFSET) + int(ROOTFS_PARTITION_SIZE)
			cmdlist.append('parted -s %s unit KiB mkpart rootfs1 ext2 %s %s' % (EMMC_IMAGE, ROOTFS_PARTITION_OFFSET, PARTED_END_ROOTFS1 ))
			PARTED_END_KERNEL2 = int(SECOND_KERNEL_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
			cmdlist.append('parted -s %s unit KiB mkpart kernel2 %s %s' % (EMMC_IMAGE, SECOND_KERNEL_PARTITION_OFFSET, PARTED_END_KERNEL2 ))
			PARTED_END_ROOTFS2 = int(SECOND_ROOTFS_PARTITION_OFFSET) + int(ROOTFS_PARTITION_SIZE)
			cmdlist.append('parted -s %s unit KiB mkpart rootfs2 ext2 %s %s' % (EMMC_IMAGE, SECOND_ROOTFS_PARTITION_OFFSET, PARTED_END_ROOTFS2 ))
			PARTED_END_KERNEL3 = int(THRID_KERNEL_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
			cmdlist.append('parted -s %s unit KiB mkpart kernel3 %s %s' % (EMMC_IMAGE, THRID_KERNEL_PARTITION_OFFSET, PARTED_END_KERNEL3 ))
			PARTED_END_ROOTFS3 = int(THRID_ROOTFS_PARTITION_OFFSET) + int(ROOTFS_PARTITION_SIZE)
			cmdlist.append('parted -s %s unit KiB mkpart rootfs3 ext2 %s %s' % (EMMC_IMAGE, THRID_ROOTFS_PARTITION_OFFSET, PARTED_END_ROOTFS3 ))
			PARTED_END_KERNEL4 = int(FOURTH_KERNEL_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
			cmdlist.append('parted -s %s unit KiB mkpart kernel4 %s %s' % (EMMC_IMAGE, FOURTH_KERNEL_PARTITION_OFFSET, PARTED_END_KERNEL4 ))
			PARTED_END_ROOTFS4 = int(FOURTH_ROOTFS_PARTITION_OFFSET) + int(ROOTFS_PARTITION_SIZE)
			cmdlist.append('parted -s %s unit KiB mkpart rootfs4 ext2 %s %s' % (EMMC_IMAGE, FOURTH_ROOTFS_PARTITION_OFFSET, PARTED_END_ROOTFS4 ))
			PARTED_END_SWAP = int(EMMC_IMAGE_SIZE) - 1024
			cmdlist.append('parted -s %s unit KiB mkpart swap linux-swap %s %s' % (EMMC_IMAGE, SWAP_PARTITION_OFFSET, PARTED_END_SWAP ))
			cmdlist.append('dd if=/dev/zero of=%s/boot.img bs=1024 count=%s' % (self.WORKDIR, BOOT_PARTITION_SIZE ))
			cmdlist.append('mkfs.msdos -S 512 %s/boot.img' %self.WORKDIR)
			cmdlist.append("echo \"boot emmcflash0.kernel1 \'brcm_cma=440M@328M brcm_cma=192M@768M root=/dev/mmcblk0p3 rw rootwait %s_4.boxmode=1\'\" > %s/STARTUP" % (getMachineBuild(), self.WORKDIR))
			cmdlist.append("echo \"boot emmcflash0.kernel1 \'brcm_cma=440M@328M brcm_cma=192M@768M root=/dev/mmcblk0p3 rw rootwait %s_4.boxmode=1\'\" > %s/STARTUP_1" % (getMachineBuild(), self.WORKDIR))
			cmdlist.append("echo \"boot emmcflash0.kernel2 \'brcm_cma=440M@328M brcm_cma=192M@768M root=/dev/mmcblk0p5 rw rootwait %s_4.boxmode=1\'\" > %s/STARTUP_2" % (getMachineBuild(), self.WORKDIR))
			cmdlist.append("echo \"boot emmcflash0.kernel3 \'brcm_cma=440M@328M brcm_cma=192M@768M root=/dev/mmcblk0p7 rw rootwait %s_4.boxmode=1\'\" > %s/STARTUP_3" % (getMachineBuild(), self.WORKDIR))
			cmdlist.append("echo \"boot emmcflash0.kernel4 \'brcm_cma=440M@328M brcm_cma=192M@768M root=/dev/mmcblk0p9 rw rootwait %s_4.boxmode=1\'\" > %s/STARTUP_4" % (getMachineBuild(), self.WORKDIR))
			cmdlist.append('mcopy -i %s/boot.img -v %s/STARTUP ::' % (self.WORKDIR, self.WORKDIR))
			cmdlist.append('mcopy -i %s/boot.img -v %s/STARTUP_1 ::' % (self.WORKDIR, self.WORKDIR))
			cmdlist.append('mcopy -i %s/boot.img -v %s/STARTUP_2 ::' % (self.WORKDIR, self.WORKDIR))
			cmdlist.append('mcopy -i %s/boot.img -v %s/STARTUP_3 ::' % (self.WORKDIR, self.WORKDIR))
			cmdlist.append('mcopy -i %s/boot.img -v %s/STARTUP_4 ::' % (self.WORKDIR, self.WORKDIR))
			cmdlist.append('dd conv=notrunc if=%s/boot.img of=%s bs=1024 seek=%s' % (self.WORKDIR, EMMC_IMAGE, BOOT_PARTITION_OFFSET ))
			cmdlist.append('dd conv=notrunc if=/dev/%s of=%s bs=1024 seek=%s' % (self.MTDKERNEL, EMMC_IMAGE, KERNEL_PARTITION_OFFSET ))
			cmdlist.append('dd if=/dev/%s of=%s bs=1024 seek=%s' % (self.MTDROOTFS, EMMC_IMAGE, ROOTFS_PARTITION_OFFSET ))
		self.session.open(Console, title = self.TITLE, cmdlist = cmdlist, finishedCallback = self.doFullBackupCB, closeOnSuccess = True)

	def doFullBackupCB(self):
		if HaveGZkernel:
			ret = commands.getoutput(' gzip -d %s/vmlinux.gz -c > /tmp/vmlinux.bin' % self.WORKDIR)
			if ret:
				text = "Kernel dump error\n"
				text += "Please Flash your Kernel new and Backup again"
				system('rm -rf /tmp/vmlinux.bin')
				self.session.open(MessageBox, _(text), type = MessageBox.TYPE_ERROR)
				return

		cmdlist = []
		cmdlist.append(self.message)
		if HaveGZkernel:
			cmdlist.append('echo "Kernel dump OK"')
			cmdlist.append("rm -rf /tmp/vmlinux.bin")
		cmdlist.append('echo "____________________________________________________\n"')
		cmdlist.append('echo "Creating the Fullbackup..."')

		system('rm -rf %s' %self.MAINDEST)
		if not path.exists(self.MAINDEST):
			makedirs(self.MAINDEST)
		if not path.exists(self.EXTRA):
			makedirs(self.EXTRA)

		f = open("%s/imageversion" %self.MAINDEST, "w")
		f.write(self.IMAGEVERSION)
		f.close()

		if self.ROOTFSBIN == "rootfs.tar.bz2":
			system('mv %s/rootfs.tar.bz2 %s/rootfs.tar.bz2' %(self.WORKDIR, self.MAINDEST))
		else:
			system('mv %s/root.%s %s/%s' %(self.WORKDIR, self.ROOTFSTYPE, self.MAINDEST, self.ROOTFSBIN))

		if SystemInfo["HasMultiBootGB"]:
			system('mv %s/kernel.bin %s/kernel.bin' %(self.WORKDIR, self.MAINDEST))
		elif self.MTDKERNEL == "mmcblk0p1" or self.MTDKERNEL == "mmcblk0p3":
			system('mv %s/%s %s/%s' %(self.WORKDIR, self.KERNELBIN, self.MAINDEST, self.KERNELBIN))
		else:
			system('mv %s/vmlinux.gz %s/%s' %(self.WORKDIR, self.MAINDEST, self.KERNELBIN))

		if SystemInfo["HasMultiBoot"] and self.list[self.selection] == "Recovery":
			system('mv %s/disk.img %s/disk.img' %(self.WORKDIR, self.MAINDEST))
		else:
			cmdlist.append('echo "rename this file to "force" to force an update without confirmation" > %s/noforce' %self.MAINDEST)

		if self.MODEL in ("gbquad4k","gbue4k"):
			system('mv %s/boot.bin %s/boot.bin' %(self.WORKDIR, self.MAINDEST))
			system('mv %s/rescue.bin %s/rescue.bin' %(self.WORKDIR, self.MAINDEST))
			system('cp -f /usr/share/gpt.bin %s/gpt.bin' %(self.MAINDEST))

		if self.MODEL in ("gbquad", "gbquadplus", "gb800ue", "gb800ueplus", "gbultraue", "gbultraueh"):
			lcdwaitkey = '/usr/share/lcdwaitkey.bin'
			lcdwarning = '/usr/share/lcdwarning.bin'
			if path.exists(lcdwaitkey):
				system('cp %s %s/lcdwaitkey.bin' %(lcdwaitkey, self.MAINDEST))
			if path.exists(lcdwarning):
				system('cp %s %s/lcdwarning.bin' %(lcdwarning, self.MAINDEST))
		if self.MODEL == "gb800solo":
			burnbat = "%s/fullbackup_%s/%s" % (self.DIRECTORY, self.MODEL, self.DATE)
			f = open("%s/burn.bat" % (burnbat), "w")
			f.write("flash -noheader usbdisk0:gigablue/solo/kernel.bin flash0.kernel\n")
			f.write("flash -noheader usbdisk0:gigablue/solo/rootfs.bin flash0.rootfs\n")
			f.write('setenv -p STARTUP "boot -z -elf flash0.kernel: ')
			f.write("'rootfstype=jffs2 bmem=106M@150M root=/dev/mtdblock6 rw '")
			f.write('"\n')
			f.close()

		cmdlist.append('cp -r %s/* %s/' % (self.MAINDEST, self.EXTRA))

		cmdlist.append("sync")
		file_found = True

		if not path.exists("%s/%s" % (self.MAINDEST, self.ROOTFSBIN)):
			print '[ImageBackup] ROOTFS bin file not found'
			file_found = False

		if not path.exists("%s/%s" % (self.MAINDEST, self.KERNELBIN)):
			print '[ImageBackup] KERNEL bin file not found'
			file_found = False

		if path.exists("%s/noforce" % self.MAINDEST):
			print '[ImageBackup] NOFORCE bin file not found'
			file_found = False

		if SystemInfo["HasMultiBootGB"] and not self.list[self.selection] == "Recovery":
			cmdlist.append('echo "_________________________________________________\n"')
			cmdlist.append('echo "Multiboot Image created on:" %s' %self.MAINDEST)
			cmdlist.append('echo "and there is made an extra copy on:"')
			cmdlist.append('echo %s' %self.EXTRA)
			cmdlist.append('echo "_________________________________________________\n"')
			cmdlist.append('echo " "')
			cmdlist.append('echo "\nPlease wait...almost ready! "')
			cmdlist.append('echo " "')
			cmdlist.append('echo "To restore the image:"')
			cmdlist.append('echo "Use OnlineFlash in SoftwareManager"')
		elif file_found:
			cmdlist.append('echo "____________________________________________________\n"')
			cmdlist.append('echo "Fullbackup created on:" %s' %self.MAINDEST)
			cmdlist.append('echo "Extra copy of fullbackup created on:"')
			cmdlist.append('echo %s' %self.EXTRA)
			cmdlist.append('echo "____________________________________________________\n"')
			cmdlist.append('echo "Please wait...almost ready...\n"')
			cmdlist.append('echo "To restore the image:"')
			cmdlist.append('echo "Please check the manual of the receiver "')
			cmdlist.append('echo "on how to restore the image"')
		else:
			cmdlist.append('echo "____________________________________________________\n"')
			cmdlist.append('echo "Image creation failed - "')
			cmdlist.append('echo "Possible causes could be"')
			cmdlist.append('echo "     wrong back-up destination "')
			cmdlist.append('echo "     no space left on back-up device"')
			cmdlist.append('echo "     no writing permission on back-up device"')
			cmdlist.append('echo " "')

		if self.DIRECTORY == "/hdd":
			self.TARGET = self.SearchUSBcanidate()
			print "[ImageBackup] TARGET = %s" % self.TARGET
			if self.TARGET == 'XX':
				cmdlist.append('echo "\n"')
				cmdlist.append('echo "\n"')
				cmdlist.append('echo "Please wait..."')
			else:
				cmdlist.append('echo "\n"')
				cmdlist.append('echo "\n"')
				cmdlist.append('echo "__________________________________________________\n"')
				cmdlist.append('echo "There is a valid USB-flash drive detected in one "')
				cmdlist.append('echo "of the USB-ports, therefor an extra copy of the "')
				cmdlist.append('echo "back-up image will now be copied to that USB- "')
				cmdlist.append('echo "flash drive. "')
				cmdlist.append('echo "This only takes about 1 or 2 minutes"')
				cmdlist.append('echo "\n"')

				cmdlist.append('mkdir -p %s/%s' % (self.TARGET, self.IMAGEFOLDER))
				cmdlist.append('cp -r %s %s/' % (self.MAINDEST, self.TARGET))


				cmdlist.append("sync")
				cmdlist.append('echo "Backup finished and copied to your USB-flash drive"')

		cmdlist.append("sleep 2")
		cmdlist.append("umount /tmp/bi/root")
		cmdlist.append("sleep 2")
		cmdlist.append("rmdir /tmp/bi/root")
		cmdlist.append("rmdir /tmp/bi")
		cmdlist.append("rm -rf %s" % self.WORKDIR)
		cmdlist.append("sleep 5")
		cmdlist.append('echo "\n"')
		END = time()
		DIFF = int(END - self.START)
		TIMELAP = str(datetime.timedelta(seconds=DIFF))
		cmdlist.append('echo "\n\n"')
		cmdlist.append('echo "Time required for this process: %s"' %TIMELAP)
		cmdlist.append('echo "\n"')

		self.session.open(Console, title = self.TITLE, cmdlist = cmdlist, closeOnSuccess = False)

	def imageInfo(self):
		imageInfotext = _("[Full Image Backup]\n")
		imageInfotext += _("By OpenACJ") + "\n"
		imageInfotext += _("Support at") + " http://altoconsejojedi.es/\n\n"
		imageInfotext += _("[Image Info]\n")
		imageInfotext += _("Model: %s %s\n") % (getMachineBrand(), getMachineName())
		imageInfotext += _("Backup Date: %s\n") % strftime("%Y-%m-%d", localtime(self.START))

		if path.exists('/proc/stb/info/chipset'):
			imageInfotext += _("Chipset: BCM%s") % about.getChipSetString().lower().replace('\n','').replace('bcm','') + "\n"
		imageInfotext += _("Kernel: %s") % about.getKernelVersionString() + "\n"
		imageInfotext += _("CPU: %s") % about.getCPUString() + "\n"
		imageInfotext += _("Threads: %s") % about.getCpuCoresString() + "\n"
		imageInfotext += _("Enigma2 Version: %s") % getImageVersion() + "\n"
		imageInfotext += _("Enigma2 Build: %s") % getImageBuild() + "\n"

		string = getDriverDate()
		year = string[0:4]
		month = string[4:6]
		day = string[6:8]
		driversdate = '-'.join((year, month, day))
		imageInfotext += _("Drivers: %s") % driversdate + "\n"
		imageInfotext += _("Last update: %s") % getEnigmaVersionString() + "\n\n"
		imageInfotext += _("[Enigma2 Settings]\n")
		imageInfotext += commands.getoutput("cat /etc/enigma2/settings")
		imageInfotext += _("\n\n[User - bouquets (TV)]\n")
		try:
			f = open("/etc/enigma2/bouquets.tv","r")
			lines = f.readlines()
			f.close()
			for line in lines:
				if line.startswith("#SERVICE"):
					bouqet = line.split()
					if len(bouqet) > 3:
						bouqet[3] = bouqet[3].replace('"','')
						f = open("/etc/enigma2/" + bouqet[3],"r")
						userbouqet = f.readline()
						imageInfotext += userbouqet.replace('#NAME ','')
						f.close()
		except:
			imageInfotext += "Error reading bouquets.tv"

		imageInfotext += _("\n[User - bouquets (RADIO)]\n")
		try:
			f = open("/etc/enigma2/bouquets.radio","r")
			lines = f.readlines()
			f.close()
			for line in lines:
				if line.startswith("#SERVICE"):
					bouqet = line.split()
					if len(bouqet) > 3:
						bouqet[3] = bouqet[3].replace('"','')
						f = open("/etc/enigma2/" + bouqet[3],"r")
						userbouqet = f.readline()
						imageInfotext += userbouqet.replace('#NAME ','')
						f.close()
		except:
			imageInfotext += "Error reading bouquets.radio"

		imageInfotext += _("\n[Installed Plugins]\n")
		imageInfotext += commands.getoutput("opkg list_installed | grep enigma2-plugin-")

		return imageInfotext
