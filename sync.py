"""
Aerodynamic Sofa by Colin ML Burnett
"""

# Where the default config info lives (in the current dir)
DEFAULT_CONFIG_NAME = '.aerodynamicsofa.config'
VERSION = (1,0,0)


# Gets us flickr API access
import flickrapi

# Utility stuff
import datetime, time
import os, os.path
import sys

# Config follows the RFC 822
import ConfigParser

# Option parsing
import getopt


from xml.sax import make_parser, handler
import xml.sax.saxutils

#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
# Argument and main
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------

def main(args):
	"""
	Do a sync.
	"""

	# Parse the options
	kargs = parseopts(args)
	if type(kargs) == int:
		return kargs

	# Copy options locally
	ak = kargs['accesskey']
	sk = kargs['secretkey']
	uid = kargs['uid']
	quiet = kargs['quiet']
	sdir = kargs['dir']
	limit = kargs['limit']
	recurse = kargs['recurse']
	date = kargs['date']
	ids = kargs['args']


	# Pass in keys and authenticate
	f = Flickr(ak, sk)
	f.Authenticate()

	# Get user's ID
	u = f.GetUser(nsid=uid)

	# Do the sync-y!
	# Sync whatever the user requested
	if 't' in limit:	fsync_contacts(sdir, u, quiet)
	if 'f' in limit:	fsync_favorites(sdir, u, quiet)
	if 'r' in limit:	fsync_groups(sdir, u, quiet)
	if 'c' in limit:	fsync_collections(sdir, u, quiet, ids, recurse)
	if 's' in limit:	fsync_sets(sdir, u, quiet, ids, recurse)
	if 'g' in limit:	fsync_galleries(sdir, u, quiet)
	if 'p' in limit:	fsync_photos(sdir, u, quiet, ids, date)
	if 'o' in limit:	fsync_profile(sdir, u, quiet)

def parseopts(args):
	"""
	Parses the options and returns relevant info or -1 on fail.
	"""

	# Parse out options
	lopts, args = getopt.getopt(args, 'c:d:hl:qr', ['accesskey=', 'secretkey=', 'uid='])

	# Map options to dictionary (yes, over-writing repeats)
	dopts = {}
	for a in lopts:
		dopts[a[0]] = a[1]


	if '-h' in dopts:
		print """Aerodynamic Sofa ' + '.'.join([str(z) for z in VERSION]) + ' by Colin ML Burnett

Syncs all photo data locally as a backup.  This includes title, comments,
favorites, metadata, tags, sets, collections, galleries, contacts, groups, etc.
Everything that can be synced is synced.  Mostly.  It would be possible to sync
things like members of a group but the goal of this is not to replicate Flickr
but to sync *YOUR* data from Flickr.

Sufficient metadata should exist that it can be matched to an original
file if necessary for possible recreation of your photostream.

Options:
  -c FILE     Specify the config file location (default: .aerodynamicsofa.config)
  -h          Show this help
  -q          Quiet the output so write nothing while processing stats
 --accesskey  The Flickr API access key
 --secretkey  The Flickr API secret key
 --uid        The Flickr user ID
  -l OPTS     Limit the sync (any order of characters):
               c    Collections
               f    Favorites
               g    Galleries
               p    Photos
               r    Groups
               s    Sets
               t    Contacts
               o    Profile
  -r          Recursive as appropriate but only if ID\'s are provided.
              There are only two cases where this can be used:
               1) ID\'s provided are of collections, then all sets and photos in
                  said collections are synced.
               2) ID\'s provided are of sets, then all photos in said sets are
                  synced.
              If this is provided for `-l p` then it is an error.
  -d DATE     Sync photos that were popular on DATE (there is a limited window
              that flickr permits access to said statistical information).
              DATE can be of the form \'DATE1|DATE2\' where they specify a date range.
              You will need to quote this argument since the pipe will be
              intercepted by the shell.  Single quotes are sufficient.
              You may not specific ID\'s with a date.
  [ID ID...]  Any number of ID\'s may be supplied that are specifically synced
              Collections, Photos, and Sets accept ID\'s and these options are then
              in the -l OPTS list to avoid ambiguity in what the ID\'s belong.
              Groups, Favorites, Galleries, and Contacts are not exclusive
              and may be supplied with c, p, or s.  This means that at least one
              of c, p, and s must be supplied if ID\'s are provided.


The config file is formatted per RFC 822 and has the following sections and options:

[Flickr Keys]
accesskey: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
secretkey: XXXXXXXXXXXXXXXX

[Flickr User]
uid: XXXXXXXXXXXX

[Storage]
dir: ./flickr/"""
		return 0

	# Define variables up front to know when they've been set
	ak = None
	sk = None
	uid = None
	quiet = None
	sdir = None
	limit = 'cfgoprst'
	date = None
	recurse = None

	# Path to config file
	cfgpath = None

	# Check if it should be quiet
	quiet = '-q' in dopts

	# Pull in specific config path or assume local
	if '-c' in dopts:
		cfgpath = dopts['-c']

		if not os.path.exists(dopts['-c']):
			print 'Config file does not exist at:', dopts['-c']
			return -1

	# None specific, use the default in the CWD
	else:
		cfgpath = DEFAULT_CONFIG_NAME

	# Parse date format
	if '-d' in dopts:
		date = []
		for a in dopts['-d'].split('|'):
			date.append(datetime.datetime.strptime(a, '%Y-%m-%d'))

		date = tuple(date)

		if len(date) == 1:
			date = tuple([date[0], date[0]])

	# Load config if it exists (this check avoids the need to *have* a config and if none is provided then all options must come in as args)
	if os.path.exists(cfgpath):
		cfg = ConfigParser.SafeConfigParser()
		cfg.read(cfgpath)

		if cfg.has_section('Flickr Keys'):
			if cfg.has_option('Flickr Keys', 'accesskey'):	ak = cfg.get('Flickr Keys', 'accesskey')
			if cfg.has_option('Flickr Keys', 'secretkey'):	sk = cfg.get('Flickr Keys', 'secretkey')

		if cfg.has_section('Flickr User'):
			if cfg.has_option('Flickr User', 'uid'):		uid = cfg.get('Flickr User', 'uid')

		if cfg.has_section('Storage'):
			if cfg.has_option('Storage', 'dir'):			sdir = cfg.get('Storage', 'dir')

	# Explicit options override the config
	if '--accesskey' in dopts:	ak = dopts['--accesskey']
	if '--secretkey' in dopts:	sk = dopts['--secretkey']
	if '--uid' in dopts:		uid = dopts['--uid']

	# Check for recursion
	recurse = '-r' in dopts

	# Make it a list of chars
	if '-l' in dopts:
		limit = dopts['-l']

	limit = [c for c in limit]

	# Check that no extraneous chars are present
	limit = set(limit)
	leftover = limit.difference(['c', 'f', 'g', 'o', 'p', 'r', 's', 't'])

	# Count the number of exclusive options for if ID's are presented
	exclusive_count = 0
	if 'c' in limit: exclusive_count += 1
	if 'p' in limit: exclusive_count += 1
	if 's' in limit: exclusive_count += 1

	# Check that options are present
	fails = []
	if ak == None:					fails.append('API access key not provided in options or in config file')
	if sk == None:					fails.append('API secret key not provided in options or in config file')
	if uid == None:					fails.append('Flickr user ID not provided in options or in config file')
	if sdir == None:				fails.append('Storage direction not specified in config file')
	if not len(limit):				fails.append('Limit is missing, nothing to sync')
	if len(leftover):				fails.append('Extraneous limit characters: ' + ''.join(leftover))
	if len(args):
		if exclusive_count == 0:	fails.append('ID\'s provided, you must provide one of c, p, or s')
		elif exclusive_count != 1:	fails.append('ID\'s provided and multiple of c, p, or s are present, only one permitted')

		if recurse:
			if 'p' in limit:		fails.append('Cannot recurse when photos is in the limit list')
		else:
			if 'c' in limit:		fails.append('Recursion is required for collection with ID\'s')
	else:
		if recurse:					fails.append('Cannot recurse when no ID\'s are provided')
	if date != None:
		if len(date) > 2:			fails.append('Can only supply one or two dates')
		if len(args):				fails.append('Date cannot accompany a list of ID\'s')

		if len(limit) > 1:			fails.append('Date can only be provided with a `-l p`')
		elif list(limit)[0] != 'p':	fails.append('Date can only be provided with a `-l p`')


	# Trailing slash
	if sdir and sdir[-1] != '/':
		sdir += '/'

	# User fail
	if len(fails):
		print 'Please fix the following errors:'
		for fail in fails:
			print '\t' + fail

		return -1

	# Substitute current directory for leading period
	if sdir[0] == '.':
		sdir = os.getcwd() + sdir[1:]

	return {'accesskey': ak, 'secretkey': sk, 'uid': uid, 'quiet': quiet, 'dir': sdir, 'limit': limit, 'recurse': recurse, 'date': date, 'args': args}


#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
# Helper functions
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------

def esc(s):
	s = s.replace('&', '&amp;')
	s = s.replace('<', '&lt;')
	s = s.replace('>', '&gt;')
	s = s.replace('"', '&quot;')
	return s

def unesc(s):
	s = xml.sax.saxutils.unescape(s)
	return s

def index(seq, f):
	"""
	How is this not in Python already?
	"""

	for i in xrange(len(seq)):
		if f(seq[i]):
			return i

	return -1

def _openxml(sdir, name):
	"""
	Checks that @sdir exists and if @name exists in @sdir then it is deleted.
	Returns a write-only file object to @name.
	"""

	# Make sure directory exists
	if not os.path.exists(sdir):
		os.mkdir(sdir)

	# Check that file doesn't exist
	fname = sdir + name
	if os.path.exists(fname):
		os.unlink(fname)

	# Open output XML file
	return open(fname, 'w')

#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
# XML reader classes
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------

class SetsXMLReader(handler.ContentHandler):
	"""
	XML reader for the sets.xml
	"""

	def __init__(self):
		# Current set id for when a <photo> is encountered
		self._sid = None

		# Dictionary keyed on set id to a dictionary of id, title, description, primary, and a list of things (photo or video id)
		self.sets = {}

		# List of set id's as presented in the file
		self.sids = []

	def startElement(self, name, attrs):
		"""
		Catches starts of <photo> and <set> and populates self.sets and self.sids appropriately.
		"""

		if name == 'set':
			# Unescape everything
			sid = xml.sax.saxutils.unescape(attrs['id'])
			t = xml.sax.saxutils.unescape(attrs['title'])
			d = xml.sax.saxutils.unescape(attrs['description'])
			prim = xml.sax.saxutils.unescape(attrs['primary'])

			# Set current set id and add to list
			self._sid = sid
			self.sids.append(sid)

			# Create data dictionary and populate
			self.sets[sid] = {}
			self.sets[sid]['id'] = sid
			self.sets[sid]['title'] = t.encode('utf-8')
			self.sets[sid]['description'] = d.encode('utf-8').replace('<br />', '\n')
			self.sets[sid]['primary'] = prim
			self.sets[sid]['things'] = []

		elif name == 'photo':
			pid = attrs['id']
			self.sets[self._sid]['things'].append(pid)

class PhotosXMLReader(handler.ContentHandler):
	"""
	XML reader for the photos.xml
	"""

	def __init__(self):
		# List of photo id's as presented in the file
		self.pids = []

	def startElement(self, name, attrs):
		"""
		Catches starts of <photo> and populates self.pids appropriately.
		"""

		if name == 'photo':
			pid = xml.sax.saxutils.unescape(attrs['id'])

			# add to list
			self.pids.append(pid)

#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
# Sync routines
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------

def fsync_contacts(sdir, u, quiet):
	"""
	Sync all the contacts.
	"""

	if not quiet: print 'Syncing contacts (t)...'

	# Pull down contacts from Flickr and write to file
	contacts = _get_contacts(u.Flickr.FlickrAPI, quiet)
	_put_contacts(contacts, sdir)


def _get_contacts(api, quiet):
	# Accumulate contacts here and key by nsid
	contacts = {}

	# Multiple pages
	pg = 1
	pages = 1
	perpage = 50

	while pg <= pages:
		ret = api.contacts_getList(per_page=perpage, page=pg)
		cntcts = ret.find('contacts')
		pages = int(cntcts.attrib['pages'])

		for cntct in cntcts.findall('contact'):
			nsid = cntct.attrib['nsid']
			user = cntct.attrib['username']
			name = cntct.attrib['realname']
			fam = bool(int(cntct.attrib['family']))
			fri = bool(int(cntct.attrib['friend']))
			ign = bool(int(cntct.attrib['ignored']))

			contacts[nsid] = {'nsid': nsid, 'name': name, 'username': user, 'family': fam, 'friend': fri, 'ignored': ign}

			if not quiet:
				print "%s as %s (%s): family=%s, friend=%s, ignored=%s" % (name, user, nsid, fam, fri, ign)

		# Next page please
		pg += 1

	return contacts

def _put_contacts(contacts, sdir):
	f = _openxml(sdir, 'contacts.xml')
	f.write('<?xml version="1.0" encoding="utf-8"?>\n')
	f.write('<asofa>\n')
	f.write('\t<contacts>\n')

	# Write contacts in order by nsid
	keys = contacts.keys()
	keys.sort()
	for key in keys:
		c = contacts[key]

		f.write('\t\t<contact nsid="%s" realname="%s" username="%s" family="%d" friend="%d" ignored="%d" />\n' % (c['nsid'], c['name'], c['username'], int(c['family']), int(c['friend']), int(c['ignored'])))

	f.write('\t</contacts>\n')
	f.write('</asofa>\n')
	f.close()


def fsync_favorites(sdir, u, quiet):
	"""
	Sync all the favorites.
	These are the favorites by the user, not photos by the user that have been favorited by others.
	"""

	if not quiet: print 'Syncing favorites (f)...'

	# Pull down favorites from Flickr and write to file
	favs = _get_favorites(u.Flickr.FlickrAPI, quiet)
	_put_favorites(favs, sdir)

def _get_favorites(api, quiet):
	# Accumulate favorites here and key by photo id
	favorites = {}

	# Multiple pages
	pg = 1
	pages = 1
	perpage = 50

	while pg <= pages:
		ret = api.favorites_getList(per_page=perpage, page=pg)
		photos = ret.find('photos')
		pages = int(photos.attrib['pages'])

		for pht in photos.findall('photo'):
			psid = pht.attrib['id']
			nsid = pht.attrib['owner']
			t = pht.attrib['title'].encode('utf-8')

			favorites[psid] = {'psid': psid, 'owner': nsid, 'title': t}

			if not quiet:
				print "%s '%s' (%s)" % (psid, t, nsid)

		# Next page please
		pg += 1

	return favorites

def _put_favorites(favorites, sdir):
	f = _openxml(sdir, 'favorites.xml')
	f.write('<?xml version="1.0" encoding="utf-8"?>\n')
	f.write('<asofa>\n')
	f.write('\t<favorites>\n')

	# Write favorites in order by psid
	keys = favorites.keys()
	keys.sort()
	for key in keys:
		c = favorites[key]

		f.write('\t\t<favorite id="%s" owner="%s" title="%s" />\n' % (c['psid'], c['owner'], c['title']))

	f.write('\t</favorites>\n')
	f.write('</asofa>\n')
	f.close()


def fsync_groups(sdir, u, quiet):
	"""
	Sync all the groups.
	These are the groups the user belongs to.
	"""

	if not quiet: print 'Syncing groups (r)...'

	# Pull down groups from Flickr and write to file
	groups = _get_groups(u.Flickr.FlickrAPI, u.getNSID(), quiet)
	_put_groups(groups, sdir)

def _get_groups(api, nsid, quiet):
	# Accumulate groups here and key by photo id
	groups = {}

	ret = api.people_getPublicGroups(user_id=nsid)
	grps = ret.find('groups')


	for grp in grps.findall('group'):
		nsid = grp.attrib['nsid']
		name = grp.attrib['name']
		admin = len(grp.attrib['admin']) and bool(int(grp.attrib['admin'])) or False
		adult = len(grp.attrib['eighteenplus']) and bool(int(grp.attrib['eighteenplus'])) or False

		groups[nsid] = {'nsid': nsid, 'name': name, 'admin': admin, 'adult': adult}

		if not quiet:
			print "%s '%s' (admin=%s, adult=%s)" % (nsid, name, admin, adult)

	return groups

def _put_groups(groups, sdir):
	f = _openxml(sdir, 'groups.xml')
	f.write('<?xml version="1.0" encoding="utf-8"?>\n')
	f.write('<asofa>\n')
	f.write('\t<groups>\n')

	# Write groups in order by nsid
	keys = groups.keys()
	keys.sort()
	for key in keys:
		c = groups[key]

		f.write('\t\t<group id="%s" name="%s" admin="%s" adult="%s" />\n' % (c['nsid'], c['name'], int(c['admin']), int(c['adult'])))

	f.write('\t</groups>\n')
	f.write('</asofa>\n')
	f.close()


def fsync_collections(sdir, u, quiet, ids, recurse):
	"""
	Sync all the collections.
	"""

	if not quiet: print 'Syncing collections (c)...'

	# Accumulate collections here and key by collection id (both flat and tree)
	collections = {}

	if len(ids):
		# Step through each collection and pull down the entire sub-tree of that collection
		# Skip a collection if it's already in @collections (it was pulled down by another collection)

		for cid in ids:
			# Skip, already done
			if cid in collections: continue

			# Pull down sub-collection
			ret = u.Flickr.FlickrAPI.collections_getTree(collection_id=cid)
			cols = ret.find('collections')

			for col in cols.findall('collection'):
				_fsync_collections_fetch(u, collections, col, None, quiet)

			# Collect set id's
			sids = []

			# Don't bother checking @recurse since it's required and check is done in parseopts()
			for cid,cs in collections.items():
				for c in cs:
					for sid in c['sets']:
						if sid not in sids: sids.append(sid)

			fsync_sets(sdir, u, quiet, sids, recurse)

	else:
		# Get all collections
		ret = u.Flickr.FlickrAPI.collections_getTree()
		cols = ret.find('collections')

		for col in cols.findall('collection'):
			_fsync_collections_fetch(u, collections, col, None, quiet)


		f = _openxml(sdir, 'collections.xml')
		f.write('<?xml version="1.0" encoding="utf-8"?>\n')
		f.write('<asofa>\n')
		f.write('\t<collections>\n')

		# Dump root collection
		_fsync_collections_dump(f, collections, collections[None])

		f.write('\t</collections>\n')
		f.write('</asofa>\n')
		f.close()

def _fsync_collections_fetch(u, collections, col, parent, quiet):
	"""
	Recursively fetch collection information from @col since @col is a hierarchial structure.
	Store into @collections.
	Parent collection ID is @parent.
	"""

	cid = col.attrib['id']
	realcid = cid.split('-')[1]

	t = col.attrib['title'].encode('utf-8')
	d = col.attrib['description']
	iconphotos = {'mosaic': {}, 'icons': []}

	if d:
		d = d.encode('utf-8')

	# Get collection information
	ret = u.Flickr.FlickrAPI.collections_getInfo(collection_id=cid)
	ret2 = ret.find('collection')

	# Pull out individual icons
	icons = ret2.find('iconphotos')
	if icons != None:
		for p in icons.findall('photo'):
			iconphotos['icons'].append(p.attrib['id'])

	# Pull out large and small icons
	if 'iconlarge' in ret2.attrib:		iconphotos['mosaic']['large'] = ret2.attrib['iconlarge']
	if 'iconsmall' in ret2.attrib:		iconphotos['mosaic']['small'] = ret2.attrib['iconsmall']

	# Pull out creation date
	ctime = ret2.attrib['datecreate']
	ctimestr = datetime.datetime.fromtimestamp(float(ret2.attrib['datecreate']))



	# Create list to store in @collections
	if parent not in collections:
		collections[parent] = []

	newcol = {'id': cid, 'title': t, 'description': d, 'icons': iconphotos, 'ctime': ctime, 'ctimestr': ctimestr}
	if parent != None:
		newcol['parent'] = parent

	# Get set ids
	newcol['sets'] = [s.attrib['id'] for s in col.findall('set')]

	# Get sub-collections
	newcol['collections'] = [c.attrib['id'] for c in col.findall('collection')]

	collections[parent].append(newcol)

	if not quiet:
		print '%s "%s"' % (cid, t)

	# Recurse into sub-collections
	for c in col.findall('collection'):
		_fsync_collections_fetch(u, collections, c, cid, quiet)

def _fsync_collections_dump(f, collections, cs, indent=2):
	"""
	Recursively dump collection information from @collections back into a tree structure.
	Iterate through the list of collections @cs.
	Indent the output by @indent tabs.
	"""

	for c in cs:
		i = '\t' * indent
		f.write(i)

		f.write('<collection id="%s"' % c['id'])
		if 'parent' in c:		f.write(' parent="%s"' % c['parent'])

		f.write(' title="%s"' % c['title'])
		f.write(' description="%s"' % c['description'])
		f.write(' ctime="%s"' % c['ctime'])
		f.write(' ctimestr="%s"' % c['ctimestr'])

		# Show as "<collection>...</collection>" if collection has stuff under it
		# ...Do check
		hassub = (c['id'] in collections) or len(c['sets'])
		hasicons = len(c['icons']['icons'])

		# ...Use check
		if hassub or hasicons:
			f.write('>\n')

			# Show icon id's in the order presented by flickr (not sure if this is L-R then T-B, or T-B then L-R, or something else
			if hasicons:
				f.write(i + '\t<icons>\n')

				keys = c['icons']['mosaic'].keys()
				keys.sort()
				for k in keys:
					f.write(i + '\t\t<mosaic url="%s" name="%s" />\n' % (c['icons']['mosaic'][k], k))

				for ic in c['icons']['icons']:
					f.write(i + '\t\t<icon id="%s" />\n' % ic)

				f.write(i + '\t</icons>\n')

			# Has sub-collections or sub-sets
			if hassub:
				if c['id'] in collections:
					_fsync_collections_dump(f, collections, collections[c['id']], indent+1)

				for subs in c['sets']:
					f.write(i + '\t')
					f.write('<set id="%s" />\n' % subs)

			f.write(i)
			f.write('</collection>\n')

		# Show as just "<collection />" if collection has nothing under it
		else:
			f.write(' />\n')


def fsync_sets(sdir, u, quiet, ids, recurse):
	"""
	Sync all of the photosets.
	"""

	if not quiet: print 'Syncing sets (s)...'

	sets = _get_sets(u.Flickr.FlickrAPI, ids, sdir, quiet)
	_put_sets(sets, sdir)

	# Recursion
	if len(ids) and recurse:
		pids = []

		# Get all photo ids in all sets
		for sid in ids:
			# Multiple pages
			pg = 1
			pages = 1
			perpage = 100

			while pg <= pages:
				ret = u.Flickr.FlickrAPI.photosets_getPhotos(photoset_id=sid, per_page=perpage, page=pg)
				photos = ret.find('photoset')
				pages = int(photos.attrib['pages'])

				for p in photos.findall('photo'):
					# Add photo id if it's unique to the set
					pid = p.attrib['id']
					if pid not in pids:
						pids.append(pid)

				pg += 1

		# Pull down photos in all sets listed
		fsync_photos(sdir, u, quiet, pids)

def _get_sets(api, ids, sdir, quiet):
	# Accumulate sets here
	sets = []

	if len(ids):
		fname = sdir + 'sets.xml'

		if not os.path.exists(fname):
			raise Exception('Must have fully synchronized sets before syncing individual sets')

		p = make_parser()
		sr = SetsXMLReader()
		p.setContentHandler(sr)
		p.parse(fname)

		# Do just the sets provided as arguments
		for sid in ids:
			ret = api.photosets_getInfo(photoset_id=sid)
			ps = ret.find('photoset')

			sid = ps.attrib['id']
			prim = ps.attrib['primary']
			t = (ps.find('title').text or '').encode('utf-8')
			d = (ps.find('description').text or '').encode('utf-8')

			st = {'id': sid, 'primary': prim, 'title': t, 'description': d, 'things': []}

			sr.sets[sid] = st

		# Pull down all sets to get the proper order
		ret = api.photosets_getList()
		ret2 = ret.find('photosets')

		# Copy set information from the xml reader into the @sets list in the order found on flickr
		for ps in ret2.findall('photoset'):
			sid = ps.attrib['id']

			# Only copy set info if present on flickr
			if sid in sr.sets:
				sets.append(sr.sets[sid])

	else:
		# Pull down all sets
		ret = api.photosets_getList()
		ret2 = ret.find('photosets')

		# Get all set information first
		for ps in ret2.findall('photoset'):
			sid = ps.attrib['id']
			prim = ps.attrib['primary']
			t = (ps.find('title').text or '').encode('utf-8')
			d = (ps.find('description').text or '').encode('utf-8')

			st = {'id': sid, 'primary': prim, 'title': t, 'description': d, 'things': []}

			sets.append(st)

	# Get photos in each set
	cnt = 0
	maxcnt = len(sets)
	if len(ids): maxcnt = len(ids) # Maximum count is of the ids if they are presented, otherwise it is the full number of sets

	for st in sets:
		# Skip sets not in the list of ids
		if len(ids) and st['id'] not in ids:
			continue

		# UI counter
		cnt += 1

		# Multiple pages
		pg = 1
		pages = 1
		perpage = 100

		while pg <= pages:
			ret = api.photosets_getPhotos(photoset_id=st['id'], per_page=perpage, page=pg)
			photos = ret.find('photoset')
			pages = int(photos.attrib['pages'])

			# Get thing id's only
			st['things'] = st['things'] + [p.attrib['id'] for p in photos.findall('photo')]

			pg += 1

		if not quiet:
			print '%4d of %4d: %s (%d things)' % (cnt, maxcnt, st['title'], len(st['things']))

	return sets

def _put_sets(sets, sdir):
	f = _openxml(sdir, 'sets.xml')
	f.write('<?xml version="1.0" encoding="utf-8"?>\n')
	f.write('<asofa>\n')
	f.write('\t<sets>\n')

	# Write groups in order presented
	for st in sets:
		_st = {}
		_st['id'] = esc(st['id'])
		_st['title'] = esc(st['title'])
		_st['description'] = esc(unesc(st['description'].replace('\n', '<br />')))
		_st['primary'] = esc(st['primary'])

		f.write('\t\t<set id="{id}" title="{title}" description="{description}" primary="{primary}">\n'.format(**_st))

		for p in st['things']:
			f.write('\t\t\t<photo id="%s" />\n' % p)

		f.write('\t\t</set>\n')


	f.write('\t</sets>\n')
	f.write('</asofa>\n')
	f.close()

def fsync_galleries(sdir, u, quiet):
	"""
	Sync all of the galleries.
	"""

	if not quiet: print 'Syncing galleries (g)...'

	# Pull down galleries from Flickr and write to file
	galleries = _get_galleries(u.Flickr.FlickrAPI, u.getNSID(), quiet)
	_put_galleries(galleries, sdir)

def _get_galleries(api, nsid, quiet):
	# Get all galleries
	galleries = []

	pg = 1
	pages = 1
	perpage = 25

	while pg <= pages:
		ret = api.galleries_getList(user_id=nsid, per_page=perpage, page=pg)

		ret2 = ret.find('galleries')
		pages = int(ret2.attrib['pages'])

		for g in ret2.findall('gallery'):
			gl = {}
			gl['id'] = g.attrib['id']
			gl['owner'] = g.attrib['owner']
			gl['created'] = g.attrib['date_create']
			gl['updated'] = g.attrib['date_update']
			gl['primary'] = g.attrib['primary_photo_id']
			gl['title'] = g.find('title').text.encode('utf-8')
			gl['description'] = g.find('description').text.encode('utf-8')

			galleries.append(gl)

		pg += 1

	# Get photos in all the galleries
	for gl in galleries:
		pg = 1
		pages = 1
		perpage = 25


		gl['things'] = []

		while pg <= pages:
			ret = api.galleries_getPhotos(gallery_id=gl['id'], per_page=perpage, page=pg)
			ret2 = ret.find('photos')
			pages = int(ret2.attrib['pages'])

			gl['things'] += [{'id': p.attrib['id'], 'owner': p.attrib['owner']} for p in ret2.findall('photo')]

			pg += 1

		if not quiet:
			print "%s '%s' (%d things)" % (gl['id'], gl['title'], len(gl['things']))

	return galleries

def _put_galleries(galleries, sdir):
	f = _openxml(sdir, 'galleries.xml')
	f.write('<?xml version="1.0" encoding="utf-8"?>\n')
	f.write('<asofa>\n')
	f.write('\t<galleries>\n')

	# Write groups in order presented
	for gal in galleries:
		f.write('\t\t<gallery id="%s" title="%s" description="%s" primary="%s">\n' % (gal['id'], (gal['title'] or '').encode('utf-8'), (gal['description'] or '').encode('utf-8'), gal['primary']))

		for p in gal['things']:
			f.write('\t\t\t<thing id="{id}" owner="{owner}" />\n'.format(**p))

		f.write('\t\t</gallery>\n')


	f.write('\t</galleries>\n')
	f.write('</asofa>\n')
	f.close()

def fsync_photos(sdir, u, quiet, ids, date=None):
	"""
	Sync all the photos.
	"""

	if not quiet: print 'Syncing photos (p)...'

	pids = []

	if len(ids):
		ids = [unicode(_z) for _z in ids]

		# Check that file doesn't exist
		fname = sdir + 'photos.xml'


		if not os.path.exists(fname):
			raise Exception('Must have fully synchronized photos before syncing individual photos')

		p = make_parser()
		pr = PhotosXMLReader()
		p.setContentHandler(pr)
		p.parse(fname)

		# Merge the photos in the appropriate order
		pids = mergePIDs(u, [_z for _z in pr.pids], [_z for _z in ids if _z not in pr.pids])

	elif date != None:
		# Get only popular photos for date @date

		# Enumerate through date range
		d = date[0]
		delta = datetime.timedelta(days=1)
		while d <= date[1]:
			print 'Dates: %s' % (d,)

			# Multiple pages
			pg = 1
			pages = 1
			perpage = 40
			first = True

			while pg <= pages:
				ret = u.Flickr.FlickrAPI.stats_getPopularPhotos(date=d, per_page=perpage, page=pg)
				ret2 = ret.find('photos')
				pages = int(ret2.attrib['pages'])

				if not quiet:
					if first:
						first = False
						print 'Getting %d total pages of photos starting with page %d: ' % (pages, pg)

					if pg % 1000 == 0:
						sys.stdout.write('M')
					elif pg % 100 == 0:
						sys.stdout.write('C')
					elif pg % 10 == 0:
						sys.stdout.write('X')
					else:
						sys.stdout.write('.')

					sys.stdout.flush()

				pids += [p.attrib['id'] for p in ret2.findall('photo') if p.attrib['id'] not in pids]

				pg += 1

			# Go to next day
			d = d + delta

			# Add newline after MCX. outputs
			print ''

	else:
		# Multiple pages
		pg = 1
		pages = 1
		perpage = 40
		first = True

		while pg <= pages:
			ret = u.Flickr.FlickrAPI.people_getPhotos(user_id=u.getNSID(), per_page=perpage, page=pg)
			ret2 = ret.find('photos')
			pages = int(ret2.attrib['pages'])

			if not quiet:
				if first:
					first = False
					print 'Getting %d total pages of photos starting with page %d: ' % (pages, pg)

				if pg % 1000 == 0:
					sys.stdout.write('M')
				elif pg % 100 == 0:
					sys.stdout.write('C')
				elif pg % 10 == 0:
					sys.stdout.write('X')
				else:
					sys.stdout.write('.')

				sys.stdout.flush()

			pids += [p.attrib['id'] for p in ret2.findall('photo')]

			pg += 1

		# Add newline after MCX. outputs
		print ''


	if date == None:
		# Save a copy of the photo id's only
		# Don't do if date is provided

		f = _openxml(sdir, 'photos.xml')
		f.write('<?xml version="1.0" encoding="utf-8"?>\n')
		f.write('<asofa>\n')
		f.write('\t<photos>\n')
		for pid in pids:
			f.write('\t\t<photo id="%s" />\n' % pid)
		f.write('\t</photos>\n')
		f.write('</asofa>\n')
		f.close()

	# Pull down each photo fully
	cnt = 0
	if len(ids):
		# Trim out empty pids
		ids = [_i for _i in ids if len(_i)]
		for pid in ids:
			# UI counter
			cnt += 1


			# Try 5 times
			plztry = 5
			while plztry > 0:
				try:
					fsync_photo(sdir, u, quiet, pid, (cnt, len(ids)))
					break
				except Exception, e:
					print e

				plztry -= 1
			if plztry == 0:
				print "Failed to fetch photo: %s" % pid
				sys.exit(-1);

	else:
		# Trim out empty pids (could be from a deleted photo as pulled down for a day's stats)
		pids = [_i for _i in pids if len(_i)]
		for pid in pids:
			# UI counter
			cnt += 1

			# Try 5 times
			plztry = 5
			while plztry > 0:
				try:
					fsync_photo(sdir, u, quiet, pid, (cnt, len(pids)))
					break
				except flickrapi.exceptions.FlickrError, e:
					if e.code == 1:
						print pid, 'Photo not found'
					else:
						print e

				except Exception, e:
					print type(e), e

				plztry -= 1
			if plztry == 0:
				print "Failed to fetch photo: %s" % pid
				sys.exit(-1);

def mergePIDs(u, existing, new):
	"""
	Merge photo id's in @new into @existing using the context to find the appropriate place.
	"""

	for pid in new:
		order = [pid]

		# PID is in existing now (put in there by processing another pid in @new)
		if pid in existing:
			continue

		# Find previous pid until a pid is found
		_p = pid
		while True:
			ret = u.Flickr.FlickrAPI.photos_getContext(photo_id=_p)
			_p = ret.find('prevphoto').attrib['id']

			_p = unicode(_p)

			if _p in existing:
				# Find where this photo id is in the existing array
				idx = index(existing, lambda x: x == _p)

				# Merge the order set of photo id's that are not in the list and insert before
				# the index of the found photo id
				if idx == 0:
					existing = order + existing
				else:
					existing = existing[0:idx] + order + existing[idx:-1]

				break

			else:
				# Could not find @_p in @existing, so append to @order and keep going
				order.append(_p)

	return existing


def fsync_photo(sdir, u, quiet, pid, counter):
	"""
	Sync a specific photo with ID @pid.
	@counter is a 2-tuple of (current counter, total) to show as a UI counter.
	"""

	p = {}
	p['info'] = fsync_photo_info(sdir, u, quiet, pid)
	p['exif'] = getExif(u, pid, p['info']['secret'])
	p['favorites'] = getFavorites(u, pid)
	p['comments'] = getComments_photo(u, pid)
	p['geo'] = getLocation(u, pid)
	p['contexts'] = getContexts(u, pid)
	p['people'] = getPeople(u, pid)

	if not quiet:
		print '%6d of %6d: %s "%s"' % (counter[0], counter[1], p['info']['id'], p['info']['title'])


	# Determine folder the file will be in
	folder = pid[-2:]

	# Make sure directory exists
	if not os.path.exists(sdir):
		os.mkdir(sdir)

	fname = sdir + 'photos/'
	if not os.path.exists(fname):
		os.mkdir(fname)

	fname += folder + '/'

	f = _openxml(fname, '%s.xml' % pid)
	f.write('<?xml version="1.0" encoding="utf-8"?>\n')
	f.write('<asofa>\n')

	f.write('\t<photo id="{id}" farm="{farm}" server="{server}" license="{license}" rot="{rot}" secret="{secret}" orignalsecret="{origsecret}" originalformat="{origformat}" media="{media}" views="{views}" ispublic="{ispublic}" isfriend="{isfriend}" isfamily="{isfamily}" permcomment="{permcomment}" permaddmeta="{permaddmeta}">\n'.format(**p['info']))
	f.write('\t\t<uploaded raw="%s">%s</uploaded>\n' % (p['info']['uploaded'], datetime.datetime.fromtimestamp(float(p['info']['uploaded']))))

	# Title may not be set
	if p['info']['title'] == None:			f.write('\t\t<title />\n')
	else:									f.write('\t\t<title>%s</title>\n' % p['info']['title'])

	# Description may not be set
	if p['info']['description'] == None:	f.write('\t\t<description />\n')
	else:									f.write('\t\t<description>%s</description>\n' % p['info']['description'])

	# Location may not be set
	if p['geo'] == None:
		f.write('\t\t<location />\n')
	else:
		f.write('\t\t<location latitude="{latitude}" longitude="{longitude}" accuracy="{accuracy}" />\n'.format(**p['geo']))

	# EXIF
	if p['exif'] == None or len(p['exif']) == 0:
		f.write('\t\t<exifs />\n')
	else:
		f.write('\t\t<exifs>\n')
		for ex in p['exif']:
			f.write('\t\t\t<exif tagspace="{tagspace}" tagspaceid="{tagspaceid}" tag="{tag}" raw="{raw}" label="{label}" />\n'.format(**ex))
		f.write('\t\t</exifs>\n')


	# Contexts
	f.write('\t\t<contexts>\n')

	for s in p['contexts']['sets']:			f.write('\t\t\t<set id="%s" />\n' % s)
	for s in p['contexts']['pools']:		f.write('\t\t\t<pool id="%s" />\n' % s)
	for s in p['contexts']['galleries']:	f.write('\t\t\t<gallery id="%s" />\n' % s)

	f.write('\t\t</contexts>\n')

	# Notes
	if len(p['info']['notes']) == 0:
		f.write('\t\t<notes />\n')
	else:
		f.write('\t\t<notes>\n')

		for note in p['info']['notes']:
			f.write('\t\t\t<note id="{id}" author="{author}" x="{x}" y="{y}" w="{w}" h="{h}">{note}</note>\n'.format(**note))

		f.write('\t\t</notes>\n')

	# People
	if len(p['people']) == 0:
		f.write('\t\t<people />\n')
	else:
		f.write('\t\t<people>\n')

		for prs in p['people']:
			if 'x' in prs:	f.write('\t\t\t<person nsid="{nsid}" username="{username}" realname="{realname}" added_nsid="{added_nsid}" x="{x}" y="{y}" w="{w}" h="{h}" />\n'.format(**prs))
			else:			f.write('\t\t\t<person nsid="{nsid}" username="{username}" realname="{realname}" added_nsid="{added_nsid}" />\n'.format(**prs))

		f.write('\t\t</people>\n')

	# Tags
	if len(p['info']['tags']) == 0:
		f.write('\t\t<tags />\n')
	else:
		f.write('\t\t<tags>\n')

		for tag in p['info']['tags']:
			f.write('\t\t\t<tag id="{id}" author="{author}" raw="{raw}">{tag}</note>\n'.format(**tag))

		f.write('\t\t</tags>\n')

	# Favorites
	if len(p['favorites']) == 0:
		f.write('\t\t<favorites />\n')
	else:
		f.write('\t\t<favorites>\n')

		for fav in p['favorites']:
			f.write('\t\t\t<favorite nsid="{nsid}" username="{username}" date="{favdate}" />\n'.format(**fav))

		f.write('\t\t</favorites>\n')

	# Comments
	if len(p['comments']) == 0:
		f.write('\t\t<comments />\n')
	else:
		f.write('\t\t<comments>\n')

		for c in p['comments']:
			f.write('\t\t\t<comment nsid="{nsid}" username="{name}" date="{createdate}">{text}</comment>\n'.format(**c))

		f.write('\t\t</comments>\n')

	f.write('\t</photo>\n')
	f.write('</asofa>')
	f.close()

def fsync_photo_info(sdir, u, quiet, pid):
	"""
	Fetch the "info" for a photo.
	This includes: id, farm & server, license, rotation, secrets for accesing the original, date uploaded, media type,
	 total number of views, public/friend/family visibility flags, permissions, title, description, notes, and tags.
	"""

	ret = u.Flickr.FlickrAPI.photos_getInfo(photo_id=pid)
	p = ret.find('photo')

	# Put all info about a photo in this dictionary
	photo = {}

	# Basic photo stuff from photos.getInfo()
	photo['id'] = pid.encode('utf-8')
	photo['farm'] = int(p.attrib['farm'])
	photo['server'] = int(p.attrib['server'])
	photo['license'] = p.attrib['license']
	photo['rot'] = p.attrib['rotation']
	photo['secret'] = p.attrib['secret']
	photo['origsecret'] = p.attrib['originalsecret']
	photo['origformat'] = p.attrib['originalformat']
	photo['uploaded'] = p.attrib['dateuploaded']
	photo['media'] = p.attrib['media']
	photo['views'] = p.attrib['views']

	v = p.find('visibility')
	photo['ispublic'] = int(v.attrib['ispublic'])
	photo['isfriend'] = int(v.attrib['isfriend'])
	photo['isfamily'] = int(v.attrib['isfamily'])

	v = p.find('permissions')
	photo['permcomment'] = int(v.attrib['permcomment'])
	photo['permaddmeta'] = int(v.attrib['permaddmeta'])

	photo['title'] = p.find('title').text
	photo['description'] = p.find('description').text

	if photo['title'] != None:				photo['title'] = photo['title'].encode('utf-8')
	if photo['description'] != None:		photo['description'] = photo['description'].encode('utf-8')

	photo['notes'] = []
	for note in p.find('notes').findall('note'):
		n = {}
		n['id'] = note.attrib['id']
		n['author'] = note.attrib['author']
		n['x'] = int(note.attrib['x'])
		n['y'] = int(note.attrib['y'])
		n['w'] = int(note.attrib['w'])
		n['h'] = int(note.attrib['h'])
		n['note'] = note.text.encode('utf-8')

		photo['notes'].append(n)

	photo['tags'] = []
	for tag in p.find('tags').findall('tag'):
		t = {}
		t['id'] = tag.attrib['id']
		t['author'] = tag.attrib['author']
		t['raw'] = tag.attrib['raw'].encode('utf-8')
		t['tag'] = tag.text.encode('utf-8')

		photo['tags'].append(t)

	return photo

def getFavorites(u, pid):
	"""
	Fetch the favorites for the photo with ID @pid.
	"""

	favret = []

	pg = 1
	pages = 1
	perpage = 25

	while pg <= pages:
		ret = u.Flickr.FlickrAPI.photos_getFavorites(photo_id=pid, per_page=perpage, page=pg)

		photo = ret.find('photo')
		pages = int(photo.attrib['pages'])

		persons = photo.getchildren()
		for person in persons:
			nsid = person.attrib['nsid']
			uname = person.attrib['username'].encode('utf-8')
			fdate = person.attrib['favedate']

			fdt = datetime.datetime.fromtimestamp(float(fdate))

			z = {'nsid': nsid, 'username': uname, 'date': fdt, 'favdate': fdate}
			favret.append(z)

		pg += 1

	return favret

def getComments_photo(u, pid):
	"""
	Get comments on the photo with ID @pid.
	"""

	ret = u.Flickr.FlickrAPI.photos_comments_getList(photo_id=pid)
	return _getComments(ret)

def getComments_photoset(u, pid):
	"""
	Get comments on the photoset with ID @pid.
	"""

	ret = u.Flickr.FlickrAPI.photoset_comments_getList(photoset_id=pid)
	return _getComments(ret)

def _getComments(ret):
	"""
	Base function to actually put down comments by processing the API return in @ret.
	"""

	cmntret = []

	cmmts = ret.find('comments')

	# Iterate through each comment
	comments = cmmts.getchildren()
	for comment in comments:
		cid = comment.attrib['id']
		author = comment.attrib['author'].encode('utf-8')
		authorname = comment.attrib['authorname'].encode('utf-8')
		cdate = comment.attrib['datecreate']
		txt = comment.text.encode('utf-8')

		cdt = datetime.datetime.fromtimestamp(float(cdate))

		z = {'nsid': author, 'name': authorname, 'date': cdt, 'createdate': cdate, 'text': txt}
		cmntret.append(z)

	return cmntret

def getExif(u, pid, secret):
	"""
	Tries to pull down EXIF data on the photo @pid with secret @secret, None on permission denied.
	"""

	# This does not always work.  Sometimes Flickr has the EXIF but does not return it.
	# I have not looked into why this query is inconsistent.
	try:
		ret = u.Flickr.FlickrAPI.photos_getExif(photo_id=pid, secret=secret)
	except flickrapi.exceptions.FlickrError, e:
		if e.code == 2:
			# Permission denied, user bans EXIF from being read
			return None
		else:
			# Some other error so reraise it
			raise

	p = ret.find('photo')

	# Iterate through each EXIF field
	exifret = []
	for ex in p.findall('exif'):
		e = {}
		e['tagspace'] = ex.attrib['tagspace'].encode('utf-8')
		e['tagspaceid'] = ex.attrib['tagspaceid'].encode('utf-8')
		e['tag'] = ex.attrib['tag'].encode('utf-8')
		e['label'] = ex.attrib['label'].encode('utf-8')
		e['raw'] = ex.find('raw').text
		if e['raw'] != None:
			e['raw'] = e['raw'].encode('utf-8')

		c = ex.find('clean')
		if c:
			e['clean'] = c.text.encode('utf-8')

		exifret.append(e)

	# Sort by tagspace then tagspaceid then tag then raw value
	# I have no idea if the ordering returned by flickr is random or a specific ordering (perhaps file-order)
	# but I'm assuming random and avoiding that issue by forcing a sort order
	# By forcing a sort order I can be assured that diff'ing the XML files will not yield
	# false changes by merely being presented a random order from flickr
	exifret.sort(_getExifSort)

	return exifret

def _getExifSort(a,b):
	"""
	Comparison method for sorting two EXIF fields.
	"""

	ret = cmp(a['tagspace'], b['tagspace'])
	if ret != 0:
		return ret

	ret = cmp(a['tagspaceid'], b['tagspaceid'])
	if ret != 0:
		return ret

	ret = cmp(a['tag'], b['tag'])
	if ret != 0:
		return ret

	return cmp(a['raw'], b['raw'])

def getLocation(u, pid):
	"""
	Get location (lat/long) of a photo with ID @pid.
	Return None if no location information is set on the photo
	"""

	try:
		ret = u.Flickr.FlickrAPI.photos_geo_getLocation(photo_id=pid)
	except flickrapi.exceptions.FlickrError, e:
		if e.code == 2:
			# No location
			return None
		else:
			# Some other error so reraise it
			raise

	p = ret.find('photo')
	l = p.find('location')

	lat = l.attrib['latitude']
	log = l.attrib['longitude']
	acc = l.attrib['accuracy']

	return {'latitude': lat, 'longitude': log, 'accuracy': acc}

def getContexts(u, pid):
	"""
	Get the contexts of the photo with ID @pid.
	Flickr considers only sets and pools as "context" for a photo but I have included
	galleries in this definition since it seems to fit.
	"""

	ret = u.Flickr.FlickrAPI.photos_getAllContexts(photo_id=pid)

	# Get the sets and pools the photo is in
	contexts = {}
	contexts['sets'] = [s.attrib['id'] for s in ret.findall('set')]
	contexts['pools'] = [p.attrib['id'] for p in ret.findall('pool')]


	# Get galleries
	# Flickr does not consider a gallery a "context" but I will to consolidate them
	pg = 1
	pages = 1
	perpage = 25

	while pg <= pages:
		ret = u.Flickr.FlickrAPI.galleries_getListForPhoto(photo_id=pid, per_page=perpage, page=pg)

		ret2 = ret.find('galleries')
		pages = int(ret2.attrib['pages'])

		contexts['galleries'] = [g.attrib['id'] for g in ret2.findall('gallery')]

		pg += 1


	return contexts

def getPeople(u, pid):
	"""
	Get the people (like notes) in the photo with ID @pid.
	"""

	ret = u.Flickr.FlickrAPI.photos_people_getList(photo_id=pid)
	ret2 = ret.find('people')

	people = []

	for p in ret2.findall('person'):
		prs = {}
		prs['nsid'] = p.attrib['nsid']
		prs['username'] = p.attrib['username']
		prs['realname'] = p.attrib['realname']
		prs['added_nsid'] = p.attrib['added_by']

		# Optional so condition only on 'x' in fsync
		if 'x' in p.attrib:
			prs['x'] = p.attrib['x']
			prs['y'] = p.attrib['y']
			prs['w'] = p.attrib['w']
			prs['h'] = p.attrib['h']

		people.append(prs)

	return people


def fsync_profile(sdir, u, quiet):
	"""
	Sync the auth's user profile.
	"""

	prof = _get_profile(u.Flickr.FlickrAPI, u.getNSID(), quiet)
	_put_profile(prof, sdir)

def _get_profile(api, nsid, quiet):
	# Get basic user information
	ret = api.people_getInfo(user_id=nsid)
	p = ret.find('person')

	# Accumulate profile here
	prof = {}

	prof['nsid'] = p.attrib['nsid']
	prof['ispro'] = p.attrib['ispro']
	prof['username'] = p.find('username').text
	prof['realname'] = p.find('realname').text
	prof['mbox'] = p.find('mbox_sha1sum').text
	prof['loc'] = p.find('location').text

	prof['url'] = {}
	prof['url']['photos'] = p.find('photosurl').text
	prof['url']['profile'] = p.find('profileurl').text
	prof['url']['mobile'] = p.find('mobileurl').text

	prof['firstphoto'] = p.find('photos').find('firstdate').text
	prof['firstphotostr'] = datetime.datetime.fromtimestamp(float(prof['firstphoto']))
	prof['cnt'] = p.find('photos').find('count').text
	prof['vws'] = p.find('photos').find('views').text


	# Get tags
	ret = api.tags_getListUser()
	ret2 = ret.find('who')
	ret3 = ret2.find('tags')

	#  Pull out tags
	prof['tags'] = []
	for t in ret3.findall('tag'):
		prof['tags'].append(t.text.encode('utf-8'))

	# Force order of tags so random order doesn't affect file history
	prof['tags'].sort()


	# Get preferences
	prof['prefs'] = {}

	ret = api.prefs_getContentType()
	prof['prefs']['contenttype'] = ret.find('person').attrib['content_type']

	ret = api.prefs_getGeoPerms()
	prof['prefs']['geoperms'] = ret.find('person').attrib['geoperms']
	prof['prefs']['importgeoexif'] = ret.find('person').attrib['importgeoexif']

	ret = api.prefs_getHidden()
	prof['prefs']['hidden'] = ret.find('person').attrib['hidden']

	ret = api.prefs_getPrivacy()
	prof['prefs']['privacy'] = ret.find('person').attrib['privacy']

	ret = api.prefs_getSafetyLevel()
	prof['prefs']['safety'] = ret.find('person').attrib['safety_level']

	return prof

def _put_profile(prof, sdir):
	f = _openxml(sdir, 'profile.xml')
	f.write('<?xml version="1.0" encoding="utf-8"?>\n')
	f.write('<asofa>\n')
	f.write('\t<profile nsid="%s" username="%s" realname="%s">\n' % (prof['nsid'], prof['username'], prof['realname']))
	f.write('\t\t<mbox>%s</mbox>\n' % prof['mbox'])
	f.write('\t\t<location>%s</location>\n' % prof['loc'])
	f.write('\t\t<firstphoto date="%s" datestr="%s" />\n' % (prof['firstphoto'], prof['firstphotostr']))
	f.write('\t\t<numphotos>%s</numphotos>\n' % prof['cnt'])
	f.write('\t\t<views>%s</views>\n' % prof['vws'])

	f.write('\t\t<preferences')
	keys = prof['prefs'].keys()
	keys.sort()
	for k in keys:						f.write(' %s="%s"' % (k, prof['prefs'][k]))
	f.write(' />\n')

	for k,v in prof['url'].items():		f.write('\t\t<url_%s>%s</url_%s>\n' % (k, v, k))
	f.write('\t\t<tags>\n')
	for t in prof['tags']:				f.write('\t\t\t<tag val="%s" />\n' % esc(t))
	f.write('\t\t</tags>\n')
	f.write('\t</profile>\n')
	f.write('</asofa>\n')
	f.close()


#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
# Objects
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------


class Flickr:
	"""
	Container to wrap the flickrapi module.
	"""

	def __init__(self, api_key, secret_key=None):
		self._Flickr = flickrapi.FlickrAPI(api_key, secret_key, format='etree')

	def getFlickrAPI(self): return self._Flickr
	FlickrAPI = property(getFlickrAPI, doc='Gets the flickrapi object')

	def Authenticate(self, perms='write'):
		(token, frob) = self.FlickrAPI.get_token_part_one(perms)
		if not token:
			raw_input('A browser window should be opening.  After authorizing this application in the browser, please press ENTER here.')

		self.FlickrAPI.get_token_part_two((token, frob))

	def GetUser(self, nsid=None, email=None, username=None):
		if username != None:
			rsp = self.FlickrAPI.people_findByUsername(username=username)
			nsid = rsp[0].attrib['nsid']

		elif email != None:
			rsp = self.FlickrAPI.people_findByEmail(email=email)
			nsid = rsp[0].attrib['nsid']

		if nsid == None:
			raise Exception("Must supply an NSID, username, or email")

		return User(self, nsid)


class User:
	"""
	Represents a user.
	Flickr, NSID, Username, RealName, IsPro, Location, PhotosURL, and ProfileURL are immediately available.
	All other properties are dynamically loaded on demand.
	"""

	def __init__(self, flickr, nsid):
		self._Flickr = flickr
		self._NSID = nsid

		info = self.Flickr.FlickrAPI.people_getInfo(user_id=self.NSID)

		self._Username = info[0].find('username').text
		self._RealName = info[0].find('realname').text

		self._IsPro = info[0].attrib['ispro'] != 0
		self._Location = info[0].find('location').text
		self._PhotosURL = info[0].find('photosurl').text
		self._ProfileURL = info[0].find('profileurl').text

		self._Photosets = None

	def getFlickr(self): return self._Flickr
	Flickr = property(getFlickr)

	def getNSID(self): return self._NSID
	NSID = property(getNSID)

	def getUsername(self): return self._Username
	Username = property(getUsername)

	def getRealName(self): return self._RealName
	RealName = property(getRealName)


	def getIsPro(self): return self._IsPro
	IsPro = property(getIsPro)

	def getLocation(self): return self._Location
	Location = property(getLocation)

	def getPhotosURL(self): return self._PhotosURL
	PhotosURL = property(getPhotosURL)

	def getProfileURL(self): return self._ProfileURL
	ProfileURL = property(getProfileURL)





if __name__ == "__main__":
	# Trim off the 0th argument that is the python script name
	main(sys.argv[1:])

