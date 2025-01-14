/* nprenet@gmail.com, 12/2024-01/2025
 *
 * Drawing tool for annotating charters.
 *
 * Interface:
 *
 * Selection 
 * 	- click to select a path		✓
 * 	- Alt-click anywhere selects all paths  ✓
 * 	- Ctrl-click for multi-selection        ✓
 *	- In both cases, get out of other modes ✓
 * 
 * PathDrawingMode
 * 	- double-click
 * 		+ enters/exits the mode ✓
 * 		+ start/end the path    ✓
 * 	- click to add a segment	✓
 *
 * SegmentEditMode
 * 	- click to select path
 * 	- click to select a segment
 * 		+ color selection	  ✓
 * 		+ drag to move it         ✓
 * 		+ 'd' to delete it        ✓ 
 * 	- shift-ctrl-click to select a stroke and insert a segment on it ✓
 *
 * Path move/copy/merge
 * 	- Move a path or group of paths
 * 		+ vertically  (select; up key)                 ✓
 * 		+ horizontally                           needed?
 * 	- Copy one path or more (select; shift-drag)		✓ 
 * 	- Delete one or more selected paths (select; 'd')	✓
 * 	- Merge two or more selected paths (select; 'm|v|f')	✓
 * 	 
 * History:
 * 	- save history after:
 * 		+ segment or path addition
 * 		+ segment move
 * 	- cancel last N actions (use JSON export) x (buggy)
 *
 * Masks:
 * 	- export baseline mask ✓
 * 	- export polygon mask  ✓
 * 	- vertically sorted lines before export ✓
 * 	- import masks
  		+ centerline 		✓
 * 		+ stroke width		✓
 * 		+ polygon               ✓
 * 
 *
 * TODO:
 * 	- modes should be exclusive of each other, with a single mode variable
 * 	- line merging functionality: make it more robust to accidental selection of all paths or allow reversion
 */

//paper.install(window);


//window.onload = function(){

function annotateLines(){

	var canvas = document.getElementById("myCanvas");
	paper.setup(canvas);
	
	paper.settings.handleSize = 6;
	paper.settings.hitTolerance = 6;
	var defaultStrokeWidth = 6;

	var charter = null;
	var charterLayer = new Layer();
	var annotationLayer = new Layer();
	var scalingFactor = 1;

	var paths = new Group();
	var currentPath = null;
	var currentSegmentIndex = -1;
	var currentSegmentHandle = null;
	var copyOn = true;

	var pathDrawingMode = false;
	var segmentEditMode = false;

	canvas.update_img = function ( file_url ){
		console.log( "canvas.update(" +  file_url + ")")
		charterLayer.activate();
		charter = new Raster( file_url );
		charter.onLoad = function() {
			console.log("Loaded image " + file_url )
			// the canvas display_size attribute is set in the containing template
			scalingFactor = canvas.display_size[1]/charter.height;
			charter.position = view.center;
			charter.fitBounds( view.bounds );
			view.draw();
			annotationLayer.activate();
			logState();
		}
	}
	
	function logState(){
			console.log(
			"caller="+this+
			"\ncanvas.size="+[canvas.width, canvas.height]+
			"\ncharter.size="+[charter.width, charter.height]+
			"\nscalingFactor="+scalingFactor+
			"\nannotationLayer.active="+annotationLayer.active+
			"\npaths.children.length="+paths.children.length+
			"\npaths.children" + paths.children+
			"\npathDrawingMode="+pathDrawingMode+
			"\nsegmentEditMode="+segmentEditMode+
			"\nCopyOn="+copyOn+
			"\ncurrentSegmentIndex="+currentSegmentIndex+
			"\ncurrentSegmentHandle="+currentSegmentHandle+
			"\ncurrentPath="+currentPath);
		console.log( paths.children )
	}

	canvas.update_img( img_url );

	/*
	 * Import segmentation data into the canvas, as paths.
	 *
	 * @param {object} pageData - line descriptions.
	 */
	canvas.importMask = function ( pageData, type ){

		if (!('lines' in pageData)){ console.log("Segmentation data empty: abort."); return }
		paths.removeChildren();
		for (line of pageData['lines']){
			if (type === 'gt'){
				paths.addChild( new Path( line['centerline'].map( (pt) => new Point( pt ).multiply(scalingFactor))));
				currentPath = paths.children.at(-1);
				currentPath.strokeColor='red';
				currentPath.strokeWidth=line['strokeWidth'];
				currentPath.smooth({type: 'geometric'});
			} else if (type==='pred'){
				paths.addChild( new Path( line['baseline'].map( (pt) => new Point( pt ).multiply(scalingFactor))));
				currentPath = paths.children.at(-1);
				currentPath.strokeColor='red';
				currentPath.strokeWidth=defaultStrokeWidth;
				currentPath.smooth({type: 'geometric'});
			}
		} 
	}

	/*
	 * Export current paths as a dictionary that describes:
	 *
	 * + centerlines
	 * + baselines
	 * + polygons (= contour of strokes)
	 *
	 */
	canvas.exportMask = function (){

		var toIntXY = function ( pt ){
		    	return [ Math.round(pt.x), Math.round(pt.y)] ;
		}

		var contour = function (id, p){

			if (p.segments.length < 2){ return null }

		    	var pointsNorth = [];
		    	var pointsSouth = [];
		    	var contourPath = new Path();
			var baselinePath = new Path();
		    	//contourPath.strokeColor='#000000'
		    	//contourPath.strokeWidth=2;

		    	var pt1 = p.segments[0].point;
		    	var pt2 = p.segments[1].point;       
		    	var vect = (pt2.subtract(pt1)).normalize( p.strokeWidth/2);
		    	var endPt1 = pt1.subtract(vect);
		    	var normalVect = vect.rotate(90);
			
			var vertebraLS = pt1.add(normalVect);
			//Marker( vertebraLS, 6, 'red' )
			var vertebraLN = pt1.subtract(normalVect);
			//Marker( vertebraLN, 6, 'green' )
		    	contourPath.add( vertebraLN );
		    	contourPath.insert(0, vertebraLS);

			baselinePath.add( vertebraLS );

		    	var pt3 = p.segments.at(-2).point;
		    	var pt4 = p.segments.at(-1).point;       
		    	var vectEnd = (pt4.subtract(pt3)).normalize( p.strokeWidth/2);
		    	var endPt2 = pt4.add(vectEnd);
		    	var normalVectEnd = vectEnd.rotate(90);

		    	if (p.segments.length > 2){

				for (var i=1; i<p.segments.length-1; i++){
					var pt = p.segments[i].point;
					var ptL = p.segments[i-1].point;
					var ptR = p.segments[i+1].point;
					var vectL = (ptL.subtract(pt)).normalize( p.strokeWidth/2);
					var vectR = (ptR.subtract(pt)).normalize( p.strokeWidth/2);
					var normalVect = vectL.subtract(vectR).divide(2).rotate(90);
					var vertebraN = pt.add(normalVect);
					//Marker( vertebraN, 6, 'green' );
					var vertebraS = pt.subtract(normalVect);
					//Marker( vertebraS, 6, 'red' );
					contourPath.add( vertebraN );
					contourPath.insert(0, vertebraS );

					baselinePath.add( vertebraS );
				}
		    	}
			var vertebraRS = pt4.add(normalVectEnd);
			var vertebraRN = pt4.subtract(normalVectEnd);
			//Marker( vertebraRS, 6, 'red' );
			//Marker( vertebraRN, 6, 'green' );
		    	contourPath.add( vertebraRN );
		    	contourPath.insert(0, vertebraRS );
			baselinePath.add( vertebraRS );
		    	contourPath.insert( contourPath.segments.length/2, endPt1);
		    	contourPath.add( endPt2 );
		    	contourPath.closed = true;
		    	contourPath.smooth({type: 'geometric'});
		    
		    	contourPath.selected = true;
		    
		    	// adding points along curves
		    	var centerline = new Path( p.segments );
			centerline.smooth({type: 'geometric'});
			var centerlineArray = [];
			for (const c of centerline.curves ){
				centerlineArray.push( c.point1 );
				var midPoint1 = c.getPointAt( c.length/3 );
				var midPoint2 = c.getPointAt( c.length*2/3 );
				centerlineArray.push( midPoint1 );
				centerlineArray.push( midPoint2 );
				centerlineArray.push( c.point2 );
			}
			centerlineArray = centerlineArray.map( (pt) => toIntXY(pt.divide(scalingFactor)));

			baselinePath.smooth({type: 'geometric'});
			var baselineArray = [];
			for (const c of baselinePath.curves ){
				baselineArray.push( c.point1 );
				var midPoint1 = c.getPointAt( c.length/3 );
				var midPoint2 = c.getPointAt( c.length*2/3 );
				baselineArray.push( midPoint1 );
				baselineArray.push( midPoint2 );
				baselineArray.push( c.point2 );
			}
			baselineArray = baselineArray.map( (pt) => toIntXY(pt.divide(scalingFactor)));

		    	var boundaryArray = [];
		    	for (const c of contourPath.curves){
				boundaryArray.push( c.point1 );
				var midPoint1 = c.getPointAt( c.length/3 );
				var midPoint2 = c.getPointAt( c.length*2/3 );
				boundaryArray.push( midPoint1 );
				boundaryArray.push( midPoint2 );
				boundaryArray.push( c.point2 );
		    	}
			boundaryArray = boundaryArray.map( (pt) => toIntXY(pt.divide(scalingFactor)));

			//markPath( baselinePath )
			contourPath.selected=false;
			//contourPath.remove();

		    	return { 'id': id, 'centerline': centerlineArray, 'baseline': baselineArray, 'boundary': boundaryArray, 'strokeWidth': p.strokeWidth }
		}

		var pageData = {'imagename': img_file, 'image_wh': [charter.width, charter.height]} ;
		var lineData = [];
		// sorting paths according to their vertical position
		sortedPaths = paths.children.toSorted((p1, p2) => p1.segments[0].point.y - p2.segments[0].point.y );
		for (var p=0; p<sortedPaths.length; p++){ 
			var data = contour(p, sortedPaths[p] ); 
			if (data !== null){ lineData.push( data ) }
		}
		
		if (lineData.length > 0){
			pageData['lines']=lineData;
			//console.log(pageData)
			return pageData;
		}
		return {}
	}

	/*
	 * Removes all existing paths from the canvas.
	 */
	canvas.eraseMask = function (){
		paths.removeChildren();
	}


	/* User interface */
	view.onDoubleClick = (ev) => {
		
		if (pathDrawingMode){
			pathDrawingMode = false;
			var p = paths.children.at(-1);
			var pIdx = paths.children.length-1;
			if (p.segments.length===1){ paths.removeChildren( pIdx, pIdx+1 );}
			else {
				p.smooth({type: 'geometric'});
				selectPath(p, false);
			}
			//historySave();
		} else {
			pathDrawingMode = true;
			var path = new Path() ;
			path.strokeColor = 'red';
			path.strokeWidth = defaultStrokeWidth;
			path.strokeCap = 'round';
			path.strokeJoin = 'round';
			selectPath(path, false);
			paths.addChild( path );
			paths.children.at(-1).add( ev.point ) ;
		};
	}

	view.onClick = (ev) => {

		console.log(ev.point, ev.point.divide(scalingFactor))

		// append a segment to a path
		if (pathDrawingMode && paths.children.length > 0){
			var p = paths.children.at(-1);
			p.add(ev.point);
			p.smooth();
			return;
		}
		// after dragging/moving a node 
		if (segmentEditMode){
			segmentEditMode = false;
			currentPath = null;
			currentSegmentIndex = -1;
			//historySave();
		}
		// select all paths: alt-click
		if (ev.modifiers.alt){
			currentPath = null;
			for (const p of paths.children){ selectPath( p, true); } 
			return
		}
		// select one path or more
		pathHitResult = getHitPath( ev.point );
		if (pathHitResult !== null && ! ev.modifiers.shift){
			var p = pathHitResult.item;
			selectPath( p, true );
			if (currentPath !== null && ev.modifiers.control){ currentPath = null }
			// unless ctrl-click, current selection cancels existing ones
			if (! ev.modifiers.control ){
				for (const op of paths.children.filter((elt) => elt !== p )){ selectPath( op, false ) }
			}
			logState()
		// or nothing
		} else {
			for (const p of paths.children){ selectPath( p, false ); }
		}
	}

	view.onKeyDown = (ev) => {
		if (Key.isDown('>')) {
			for (const p of paths.children){ p.strokeWidth += (1*p.isSelected); }
			//historySave();
		} else if (Key.isDown('<')){
			for (const p of paths.children){ p.strokeWidth -= (1*p.isSelected); }
			//historySave();
		} else if (Key.isDown('up')){
			if (currentSegmentHandle !== null){ currentSegmentHandle.remove(); }
			for (const p of paths.children){ p.translate( new Point(0, -2*p.isSelected)) } 
		} else if (Key.isDown('down')){
			if (currentSegmentHandle !== null){ currentSegmentHandle.remove(); }
			for (const p of paths.children){ p.translate( new Point(0, 2*p.isSelected)) } 
		} else if (Key.isDown('m') || Key.isDown('f') || Key.isDown('v')){
			mergePaths( paths.children.filter( (elt) => elt.isSelected ));
		} else if (Key.isDown('escape')){
			pathDrawingMode = false;
			segmentEditMode = false;
			deselectAll();
		} else if (Key.isDown('d')){
			if (currentPath !== null){
				if (currentSegmentIndex > -1){
					currentPath.removeSegment( currentSegmentIndex );
					currentPath = null;
					currentSegmentIndex = -1;
					if (currentSegmentHandle !== null){ currentSegmentHandle.remove(); }
				} else {
					deletePath( currentPath );
					currentPath = null;
				}
				//historySave();
			} else { deletePaths( paths.children.filter((p)=>p.isSelected)); }
		} 
		// every key op happens on path
		currentSegmentIndex = -1;
		/*else if (ev.modifiers.control && Key.isDown('z')){ // buggy
			//historyRestore();
		}*/
	}
	
	view.onMouseDown = (ev) => {
		//console.log("MouseDown:");
		var pathHitResult = getHitPath( ev.point );

		// Edit a segment
		if (! pathDrawingMode && pathHitResult !== null && (pathHitResult.type === 'segment' || pathHitResult.type==='stroke')){
			if (currentPath !== pathHitResult.item && currentSegmentHandle !== null){
				currentSegmentHandle.remove();
				currentSegmentHandle = null;
			}
			currentPath = pathHitResult.item;
			// clicking on a path node (="Segment") makes this node editable (drag)
			if (pathHitResult.type === 'segment'){
				currentSegmentIndex = pathHitResult.segment.index;
				// visual feedback after hitting the node
				if (currentSegmentHandle !== null){
					currentSegmentHandle.remove();
				}
				currentSegmentHandle = Marker(pathHitResult.segment.point, paper.settings.handleSize, 'red');
			// ctrl-clicking on a path stroke adds a node in the given position
			} else if ( pathHitResult.type === 'stroke' && ev.modifiers.control && ev.modifiers.shift){
				currentSegmentIndex = pathHitResult.location.curve.segment2.index;
				currentPath.insert( currentSegmentIndex, ev.point );
				//historySave();
			}/* else if ( pathHitResult.type === 'stroke' && ev.modifiers.shift ){
				currentPath = currentPath.clone();
				paths.addChild( currentPath );
			}*/
		}
	}	

	view.onMouseDrag = (ev) => { 
		// move the path node
		if (currentSegmentIndex >= 0){
			segmentEditMode = true;
			var segt = currentPath.segments[currentSegmentIndex];
			if (currentSegmentHandle !== null){ currentSegmentHandle.remove(); }
			currentPath.removeSegment( currentSegmentIndex );
			currentPath.insert( currentSegmentIndex, segt.point.x+ev.delta.x, segt.point.y+ev.delta.y);
			currentPath.smooth({type: 'geometric'});
		} else if ( ev.modifiers.shift ){
			logState()
			var clones = [];
			if (copyOn){
				for (const p of paths.children.filter((elt)=> elt.isSelected)){
					pc = p.clone();
					selectPath(p, false);
					selectPath(pc, true );
					clones.push(pc);
				}
				copyOn=false;
				paths.addChildren( clones );
			}
			
			for (const p of paths.children.filter((elt) => elt.isSelected)){
				p.translate(ev.delta);
			}
		} else if (currentPath !== null){
			currentPath.translate( ev.delta );
		}
	}

	view.onMouseUp = (ev) => {
		copyOn = true;
	}

	function selectPath( p, value ){
		if (value){
			p.selected = true;
			p.isSelected = true;
			p.strokeColor = 'blue';
		} else {
			p.selected = false;
			p.isSelected = false;
			p.strokeColor = 'red';
		}
	}

	function getHitPath( pt ){
		var hitResult = null;
		for (var p=0; p<paths.children.length; p++){
			hitResult = paths.children[p].hitTest( pt );
			if (hitResult !== null){
				paths.children[p].selected = true;
				break;
			}
		}
		return hitResult;
	}

	function deselectAll(){
		for (const p of paths.children){
			selectPath( p, false);
		}
		currentPath = null;
		currentSegmentIndex = -1;
	}

	function deletePath( path ){
		for (var p=0; p< paths.children.length; p++){ if (paths.children[p]===path){ break; } }
		paths.removeChildren(p, p+1)
	}

	function deletePaths( ps ){
		var indicesToDelete = ps.map((p) => paths.children.findIndex((e) => e===p))
		for (const i of indicesToDelete.toSorted( (x,y) => y-x)){
			paths.removeChildren(i,i+1)
		}
	}

	function Marker (pt, diam, col) {
		var p = Path.Circle( pt, diam );
		p.fillColor=col;
		return p;
	};

	function markPath( p ){
		for (s of p.segments){ Marker( s.point, 6, 'red' ); }
	}


	function mergePaths( pths ){
		/* Join paths along the x-axis */
		if (pths.length < 2){ return null; }
		xSortedPaths = pths.toSorted( (p1, p2) => p1.segments[0].point.x - p2.segments[0].point.x ) 
		for (var pi=1; pi<xSortedPaths.length; pi++){
			xSortedPaths[0].addSegments( xSortedPaths[pi].segments )
		}
		deletePaths( xSortedPaths.slice(1));
	}

	function historySave( op ){
		//console.log("historySave()");
		//history[historyCount++]=op;
	}

	function historyRestore(){
		console.log("historyRestore(): history.length = " + history.filter( (h) => h !== null ).length );
		thisOpIndex = (historyCount-1) % HISTLENGTH;
		previousOpIndex = (thisOpIndex - 1 + HISTLENGTH) % HISTLENGTH;
		previousOp = history[previousOpIndex];
		if (previousOp !== null){
			//paper.project.importSVG( previousOp.svg );
			history[thisOpIndex]=null;
			historyCount--;
		}
		segmentEditMode = false;
		pathDrawingMode = false;
	}


}

