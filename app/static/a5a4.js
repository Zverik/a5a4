function pg(link, action) {
	var page = link.parentNode.parentNode;
	if( !page.hasAttribute('page') )
		return false;
	var pages = buildPages(),
		index;
	for( index = pages.length - 1; index >= 0; index-- )
		if( pages[index] == page )
			break;
	if( index < 0 )
		return false;

	if( action == 'left' && index > 0 ) {
		page.parentNode.insertBefore(page, pages[index-1]);
		save();
	} else if( action == 'right' && index + 1 < pages.length ) {
		page.parentNode.insertBefore(pages[index+1], page);
		save();
	} else if( action == 'add' ) {
		var copy = page.cloneNode(true);
		page.parentNode.insertBefore(copy, page);
		save();
	} else if( action == 'delete' ) {
		page.parentNode.removeChild(page);
		save();
	} else if( action == 'rotate' ) {
		var pageId = page.getAttribute('page'),
			transform = pageId.length < 3 ? '' : pageId.charAt(2),
			rotated = transform == 'R' || transform == 'D',
			newTransform,
			img = page.getElementsByTagName('img');
		if( !img || !img.length )
			return false;
		if( transform == 'R' )
			newTransform = 'L';
		else if( transform == 'L' )
			newTransform = 'R';
		else if( transform == 'D' )
			newTransform = '';
		else
			newTransform = 'D';
		img[0].className = rotated ? '' : 'rotate';
		page.setAttribute('page', (pageId.length < 3 ? pageId : pageId.substring(0, 2)) + newTransform);
		save();
	}
	return false;
}

function buildPages() {
	var root = document.getElementById('pages'),
		pages = [],
		nodes = root.children, i;
	for( i = 0; i < nodes.length; i++ ) {
		if( nodes[i].hasAttribute('page') )
			pages.push(nodes[i]);
	}
	return pages;
}

function getPagesString() {
	var pages = buildPages(), i, str = '';
	for( i = 0; i < pages.length; i++ ) {
		if( str.length )
			str += ' ';
		str += pages[i].getAttribute('page');
	}
	return str;
}

function setStatus(st) {
	var panel = document.getElementById('pgstatus');
	if( st == 'modified' ) {
		panel.innerHTML = 'Modified. <a href="javascript:upload();">Save</a>';
	} else if( st == 'saving' ) {
		panel.innerHTML = 'Saving...';
	} else if( st == 'saved' ) {
		panel.innerHTML = 'Saved.';
	} else if( st == 'fail' ) {
		panel.innerHTML = 'Failed to save. <a href="javascript:upload();">Try again</a>';
	}
}

// schedule an upload
var timeout;
function save() {
	setStatus('modified');
	if( timeout )
		window.clearTimeout(timeout);
	timeout = window.setTimeout(upload, 2000);
}

function upload() {
	if( timeout )
		window.clearTimeout(timeout);
	timeout = false;
	setStatus('saving');
	var str = getPagesString(), http,
		url = window.uploadRoot + '?pages=' + encodeURIComponent(str);
	// copied from mapbbcode :)
	if (window.XMLHttpRequest) {
		http = new window.XMLHttpRequest();
	}
	if( window.XDomainRequest && (!http || !('withCredentials' in http)) ) {
		// older IE that does not support CORS
		http = new window.XDomainRequest();
	}
	if( !http ) {
		setStatus('fail');
		return;
	}

	function respond() {
		var st = http.status,
			error = (!st && http.responseText) || (st >= 200 && st < 300) ? false : (st || 499);
		setStatus(error ? 'fail' : 'saved');
	}

	if( 'onload' in http )
		http.onload = http.onerror = respond;
	else
		http.onreadystatechange = function() { if( http.readyState == 4 ) respond(); };

	try {
		http.open('GET', url, true);
		http.send(null);
	} catch( err ) {
		// most likely a security error
		setStatus('fail');
	}
}
