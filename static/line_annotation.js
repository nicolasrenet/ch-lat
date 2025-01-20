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
 * 	- click to select a segment
 * 		+ color selection		✓
 * 		+ drag to move it		✓
 * 		+ 'd' to delete it		✓ 
 * 	- shift-ctrl-click to select a stroke and insert a segment on it ✓
 *
 * Path move/copy/merge
 * 	- Move a path or group of paths
 * 		+ move baseline vertically  (select + mouse drag)	✓ 
 * 		+ line wr/ baseline, vertically (select + up key)	✓
 * 		+ horizontally                           		needed?
 * 	- Copy one path or more (select; shift-drag)			✓ 
 * 	- Delete one or more selected paths (select; 'd')		✓
 * 	- Merge two or more selected paths (select; 'm|v|f')		✓
 * 	- Merge two or more selected paths (alt. alt-shift + drag)	✓
 * 	- Cut a path at given point (select point; 'c')			✓
 * 	- (optional) prevent overlaps when thickening lines		✓
 * 	- (optional) offset baselines                                   ✓
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
 * 	- stats about line thickness
 */

//paper.install(window);


//window.onload = function(){

function annotateLines(){

	const canvas = document.getElementById("myCanvas");
	paper.setup(canvas);
	
	paper.settings.handleSize = 6;
	paper.settings.hitTolerance = 6;
	var scalingFactor = 1;

	var settings = {
		strokeWidth: 6,
		groundTruthColor: new Color(0,1,0,0.6),
		predictionColor: new Color(1,0,0,0.6),
		selectionColor: new Color(0,0,1,0.7),
		newLineColor: new Color(0,0.5,0.5,0.5),
		highlighterColor: new Color(1,1,0,0.5),
		baselineColor: new Color(.48,.04,0.08),
		smoothing: false,
		overlapHandling: false,
		overlapScope: 3,
		overlapBuffer: 2,
		baselineOffsets: false,
	}

	var charter = null;
	var charterLayer = new Layer();
	var annotationLayer = new Layer();
	var contourLayer = new Layer();

	annotationLayer.activate()
	var paths = new Group();

	var currentPath = null;
	var currentSegmentIndex = -1;
	var currentSegmentHandle = null;
	var mergedPath = null;


	const Modes = Object.freeze({
		normal: 0,
		pathDrawing: 1,
		segmentEdit: 2,
		noPathCopy: 3,
		joinPath: 4,
		preview: 5
	});

	var mode=Modes.normal;

	function updateImg( file_url ){
		charterLayer.activate();
		charter = new Raster( file_url );
		charter.onLoad = function() {
			console.log(`Loaded image ${file_url}` )
			// the canvas display_size attribute is set in the containing template
			scalingFactor = canvas.display_size[1]/charter.height;
			charter.position = view.center;
			charter.fitBounds( view.bounds );
			view.draw();
			annotationLayer.activate()
			logState();
		}
	}


	function applySettings( settingDoc ){ 
		settings = { ...settings, ...settingDoc } ;
		if (! settings.baselineOffsets){
			for (const p of paths.children){ p.baselineOffset=0 }
			previewMaskOn( false );
		}
	}

	function getSetting( key ){ return settings[key] }
	
	function logState(){
			console.log(
			"caller="+this+
			"\ncanvas.size="+[canvas.width, canvas.height]+
			"\ncharter.size="+[charter.width, charter.height]+
			`\nscalingFactor=${scalingFactor}` +
			`\nannotationLayer.active=${annotationLayer===project.activeLayer} (${annotationLayer.children.length}  children)` +
			`\ncharterLayer.active=${charterLayer===project.activeLayer} (${charterLayer.children.length} children)` +
			`\ncontourLayer.active=${contourLayer===project.activeLayer} (${contourLayer.children.length} children)` +
			`\npaths.children.length=${paths.children.length}` +
			`\npaths.children=${paths.children}` +
			`\npathDrawingMode=${mode==Modes.pathDrawing}` +
			`\nsegmentEditMode=${mode===Modes.segmentEdit}` +
			`\npreviewMode=${mode===Modes.preview}` +
			`\nCopyOn=${mode!==Modes.noPathCopy}` +
			`\ncurrentSegmentIndex=${currentSegmentIndex}` +
			`\ncurrentSegmentHandle=${currentSegmentHandle}` +
			`\ncurrentPath=${currentPath}`); 
		console.log( paths.children )
	}

	updateImg( img_url );


	var importMask = ( pageData, type ) => {
		
		logState()
		if (!('lines' in pageData)){ console.log("Segmentation data empty: abort."); return }
		paths.removeChildren();
		for (line of pageData['lines']){
			var strokeWidth = settings.strokeWidth;
			if (type === 'gt'){
				var p = new Path( line['centerline'].map( (pt) => new Point( pt ).multiply(scalingFactor)));
				p.baselineOffset = 0 ; 
				if (settings.baselineOffsets && 'baselineOffset' in line){ p.baselineOffset = line['baselineOffset'] }
				paths.addChild( p );
				strokeWidth = line['strokeWidth'];
			} else if (type==='pred'){
				if (line['baseline'].length < 2){ continue }
				var p = new Path( line['baseline'].map( (pt) => new Point( pt ).multiply(scalingFactor)))
				p.baselineOffset = 0;
				paths.addChild( p );
			}
			currentPath = paths.children.at(-1);
			currentPath.strokeWidth=strokeWidth;
			if (settings.smoothing) currentPath.smooth({type: 'geometric'});
		} 
		deselectAll();
	}



	/*
	 * Removes all existing paths from the canvas.
	 */
	var eraseMask = () => { paths.removeChildren(); }


	var checkOverlaps = (paths, selectFlag=true) => {
		var sortedPaths = paths.children.filter( p => p.segments.length > 1).toSorted((p1, p2) => p1.segments[0].point.y - p2.segments[0].point.y );
		var copiedPaths = []
		for (const p of sortedPaths){
			const copy = p.clone(insert=false);
			copy.strokeWidth += settings.overlapBuffer;
			copiedPaths.push( copy );
		}
		var checkContours = [] // just for checking: hidden
		var contours = []
		var baselines = []
		for (var p=0; p<copiedPaths.length; p++){ 
			// draw contours, but not the baseline!
			checkContours.push( contour(p, copiedPaths[p], false ).contourPath);
			checkContours.at(-1).visible=false;
			copiedPaths[p].remove();
			contour_dictionary = contour(p, sortedPaths[p])
			var [ct, bl] = ['contourPath', 'baselinePath'].map( k => contour_dictionary[k] );
			ct.selected = true
			sortedPaths[p].selected=true
			contours.push( ct ); 
			baselines.push( bl );
		}
		for (var p=0; p<contours.length-1; p++){
			for (var nghbr=p+1; nghbr<contours.length && nghbr<=p+settings.overlapScope; nghbr++){
				if (checkContours[p].intersects( checkContours[nghbr]) && settings.overlapHandling){
					console.log(`Polygons ${p} and ${nghbr} intersect.`)
					selectPath(sortedPaths[p], selectFlag);
					selectPath(sortedPaths[nghbr], selectFlag);
				}
			}
		}
	}

	var previewMaskOn = ( on ) => {
		if (on){
			if (mode===Modes.preview){ return } else { mode=Modes.preview }
			deselectAll();
			contourLayer.activate();
			checkOverlaps( paths, true ); // true = overlapping paths are highlighted
			contourLayer.visible = true;	
			annotationLayer.activate();
		} else if (mode===Modes.preview) { 
			contourLayer.removeChildren(); 
			for (const p of paths.children){ selectPath(p,false);}
			mode = Modes.normal;
		}
	}

	var exportMask = () => {

		var pageData = {'imagename': img_file, 'image_wh': [charter.width, charter.height]} ;
		var lineData = [];
		// sorting paths according to their vertical position
		var sortedPaths = paths.children.filter( p => p.segments.length > 1).toSorted((p1, p2) => p1.segments[0].point.y - p2.segments[0].point.y );
		console.log("export()" + sortedPaths)
		contourLayer.activate()
		for (var p=0; p<sortedPaths.length; p++){ 
			contour_dictionary = contour(p, sortedPaths[p])
			var [ct,data] = ['contourPath', 'data'].map( k => contour_dictionary[k] );
			ct.selected=true;
			if (data !== null){ lineData.push( data ) }
		}
		annotationLayer.activate()
		mode = Modes.preview

		if (lineData.length > 0){
			pageData['lines']=lineData;
			//console.log(pageData)
			return pageData;
		}
		return {}
	}

	/* User interface */
	view.onDoubleClick = (ev) => {
		
		if (mode === Modes.pathDrawing){
			mode=Modes.normal;
			var p = paths.children.at(-1);
			var pIdx = paths.children.length-1;
			if (p.segments.length===1){ paths.removeChildren( pIdx, pIdx+1 );}
			else {
				if (settings.smoothing) p.smooth({type: 'geometric'});
				selectPath(p, false);
			}
			//historySave();
		} else {
			mode = Modes.pathDrawing;
			var path = new Path() ;
			path.strokeColor = settings.newLineColor;
			path.strokeWidth = settings.strokeWidth;
			//path.strokeCap = 'round';
			path.strokeJoin = 'round';
			path.baselineOffset = 0; // not used unless baselineOffset enabled
			selectPath(path, false);
			paths.addChild( path );
			paths.children.at(-1).add( ev.point ) ;
		};
	}

	view.onClick = (ev) => {

		//console.log(ev.point, ev.point.divide(scalingFactor))
		//eraseSegmentHandle();
		if (mode===Modes.preview){ previewMaskOn( false ) }
		if (mode===Modes.joinPath){
			mode=Modes.normal;
			currentPath.remove();
			currentPath = null;
			mergedPath = null;
			return;
		}
		// append a segment to a path
		if (mode===Modes.pathDrawing && paths.children.length > 0){
			var p = paths.children.at(-1);
			p.add(ev.point);
			if (settings.smoothing) p.smooth();
			return;
		}
		// after dragging/moving a node 
		if (mode===Modes.segmentEdit){
			logState()
			mode=Modes.normal;
			deselectAll();
			return
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
			eraseSegmentHandle();
			mode=Modes.normal;
			for (const p of paths.children){ selectPath( p, false ); }
		}
	}

	view.onKeyUp = (ev) => { eraseSegmentHandle() }

	view.onKeyDown = (ev) => {
		if (Key.isDown('>')) {
			// check overlaps, deselect intersecting
			if (settings.overlapHandling){
				contourLayer.activate();
				contourLayer.visible=false;
				checkOverlaps( paths, false );
				contourLayer.removeChildren();
			}
			annotationLayer.activate();
			// increment
			for (const p of paths.children){ p.strokeWidth += (1*p.isSelected);}
			//historySave();
		} else if (Key.isDown('<')){
			for (const p of paths.children){ p.strokeWidth -= (1*p.isSelected*(p.strokeWidth>1)); }
			//historySave();
		} else if (Key.isDown('up')){
			ev.preventDefault()
			eraseSegmentHandle();
			for (const p of paths.children){ 
				p.translate( new Point(0, -2*p.isSelected)); 
				p.baselineOffset += (2*p.isSelected*settings.baselineOffsets) 
			} 
		} else if (Key.isDown('down')){
			ev.preventDefault()
			if (currentSegmentHandle !== null){ currentSegmentHandle.remove(); }
			for (const p of paths.children){ 
				p.translate( new Point(0, 2*p.isSelected)) ; 
				p.baselineOffset -= (2*p.isSelected*settings.baselineOffsets)
			} 
		} else if (Key.isDown('m') || Key.isDown('f') || Key.isDown('v')){
			mergePaths( paths.children.filter( (elt) => elt.isSelected ));
			deselectAll();
		} else if (Key.isDown('s')){
			selectPaths( p => p.length <= currentPath.length );
		} else if (Key.isDown('escape')){
			mode = Modes.normal;
			deselectAll();
		} else if (Key.isDown('c') ){
			if (currentPath !== null && currentPath.segments.length > 2 && currentSegmentIndex >=1 && currentSegmentIndex < currentPath.segments.length-1 ){
				paths.addChild( new Path( currentPath.segments.slice(currentSegmentIndex)));
				paths.children.at(-1).strokeColor=settings.newLineColor;
				paths.children.at(-1).strokeWidth=settings.strokeWidth;
				currentPath.segments.splice( currentSegmentIndex+1 );
			}
		} else if (Key.isDown('d') || Key.isDown('delete')){
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
		console.log("MouseDown:");
		var pathHitResult = getHitPath( ev.point );
		// moving selection for joining paths
		if (ev.modifiers.alt && ev.modifiers.shift){
			mode = Modes.joinPath;
			currentPath = new Path( [ ev.point ]);
			currentPath.strokeWidth=30;
			currentPath.strokeColor = settings.highlighterColor;
			return
		}

		// Edit a segment
		if (mode !== Modes.pathDrawing && pathHitResult !== null && (pathHitResult.type === 'segment' || pathHitResult.type==='stroke')){
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
		eraseSegmentHandle();	
		if (mode===Modes.joinPath){
			var lastPt = currentPath.lastSegment.point
			currentPath.addSegment( lastPt.x+ev.delta.x, lastPt.y+ev.delta.y)
			var hitResult = getHitPath( ev.point)
			if (hitResult !== null && hitResult.item !== mergedPath){
				if (mergedPath === null){ mergedPath = hitResult.item }
				else {
					mergedPath.addSegments( hitResult.item.segments )
					mergedPath.segments.sort( (s1,s2 ) => s1.point.x - s2.point.x ); 
					deletePath( hitResult.item )
				}
			}
			
		// copy the path
		} else if ( ev.modifiers.shift ){
			logState()
			var clones = [];
			if (mode !== Modes.noPathCopy){
				for (const p of paths.children.filter((elt)=> elt.isSelected)){
					pc = p.clone();
					selectPath(p, false);
					selectPath(pc, true );
					clones.push(pc);
				}
				mode=Modes.noPathCopy;
				paths.addChildren( clones );
			}
			
			for (const p of paths.children.filter((elt) => elt.isSelected)){
				p.translate(ev.delta);
			}
		} else if (currentSegmentIndex >= 0){
			mode = Modes.segmentEdit;
			var segt = currentPath.segments[currentSegmentIndex];
			//if (currentSegmentHandle !== null){ currentSegmentHandle.remove(); }
			currentPath.removeSegment( currentSegmentIndex );
			currentPath.insert( currentSegmentIndex, segt.point.x+ev.delta.x, segt.point.y+ev.delta.y);
			if (settings.smoothing) currentPath.smooth({type: 'geometric'});
		} else if (currentPath !== null){
			currentPath.translate( ev.delta );
		}
	}

	view.onMouseUp = (ev) => {
		if (mode === Modes.noPathCopy) mode = Modes.normal;
	}

	function selectPath( p, value ){
		if (value){
			p.selected = true;
			p.isSelected = true;
			p.strokeColor = settings.selectionColor;
		} else {
			p.selected = false;
			p.isSelected = false;
			p.strokeColor = settings.predictionColor;
		}
	}

	function selectPaths( filter_func ){
		if (currentPath === null){ console.log("No current selection. Abort."); return }
		relevant = paths.children.filter( p => filter_func(p) );
		for (const p of relevant){ selectPath( p, true) }
		currentPath = null;
		currentSegmentIndex = -1;
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

	function eraseSegmentHandle(){
		if (currentSegmentHandle !== null){
			currentSegmentHandle.remove();
			currentSegmentHandle = null;
		}
	}

	function deselectAll(){
		for (const p of paths.children){ selectPath( p, false); }
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


	var toIntXY = function ( pt ){
		return [ Math.round(pt.x), Math.round(pt.y)] ;
	}

	var truncate_point = function (pt_arr, max_width, max_height) {
		if (pt_arr[0] < 0){ pt_arr[0] = 0; } 
		else if (pt_arr[0] >= charter.width){ pt_arr[0] = charter.width-1; }
		if (pt_arr[1] < 0){ pt_arr[1] = 0; }
		else if (pt_arr[1] >= charter.height){ pt_arr[1] = charter.height-1; }
		return pt_arr
	}

	var contour = function (id, p, baseline=true){

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
		var endPt1 = pt1;//.subtract(vect.divide(2));
		var normalVect = vect.rotate(90);
		
		var vertebraLS = pt1.add(normalVect);
		//Marker( vertebraLS, 6, 'red' )
		var vertebraLN = pt1.subtract(normalVect);
		//Marker( vertebraLN, 6, 'green' )
		contourPath.add( vertebraLN );
		contourPath.insert(0, vertebraLS);

		//baselinePath.add( vertebraLS );

		var pt3 = p.segments.at(-2).point;
		var pt4 = p.segments.at(-1).point;       
		var vectEnd = (pt4.subtract(pt3)).normalize( p.strokeWidth/2);
		var endPt2 = pt4;//.add(vectEnd.divide(2));
		var normalVectEnd = vectEnd.rotate(90);

		if (p.segments.length > 2){

			for (var i=1; i<p.segments.length-1; i++){
				var pt = p.segments[i].point;
				var ptL = p.segments[i-1].point;
				var ptR = p.segments[i+1].point;
				var vectL = (ptL.subtract(pt)).normalize(p.strokeWidth/2);
				var vectR = (ptR.subtract(pt)).normalize(p.strokeWidth/2);
				var normalVect = vectL.subtract(vectR).divide(2).rotate(90);
				var vertebraN = pt.add(normalVect);
				//Marker( vertebraN, 6, 'green' );
				var vertebraS = pt.subtract(normalVect);
				//Marker( vertebraS, 6, 'red' );
				contourPath.insert(0, vertebraS );
				contourPath.add( vertebraN );

				//baselinePath.add( vertebraS );
			}
		}
		var vertebraRS = pt4.add(normalVectEnd);
		var vertebraRN = pt4.subtract(normalVectEnd);
		//Marker( vertebraRS, 6, 'red' );
		//Marker( vertebraRN, 6, 'green' );
		contourPath.add( vertebraRN );
		contourPath.insert(0, vertebraRS );
		//baselinePath.add( vertebraRS );
		contourPath.insert( contourPath.segments.length/2, endPt1);
		contourPath.add( endPt2 );
		contourPath.closed = true;
		if (settings.smoothing) contourPath.smooth({type: 'geometric'});
	    
		var centerlineArray = p.segments.map( (s) => toIntXY(s.point.divide(scalingFactor)));
		var boundaryArray = [];
		for (const c of contourPath.curves){
			boundaryArray.push( c.point1 );
			var midPoint1 = c.getPointAt( c.length/3 );
			var midPoint2 = c.getPointAt( c.length*2/3 );
			boundaryArray.push( midPoint1 );
			boundaryArray.push( midPoint2 );
			if (c.point2 === contourPath.curves[0].point1){ break }
			boundaryArray.push( c.point2 );
		}
		boundaryArray = boundaryArray.map( (pt) => toIntXY(pt.divide(scalingFactor)));
		boundaryArray = boundaryArray.map( (pt) => truncate_point( pt, charter.width, charter.height));

		var baselinePath = null;
		var baselineArray = [];
		if (baseline && settings.baselineOffsets) {	
			baselinePath = new Path( p.segments.map( s => s.point.add(new Point(0, p.baselineOffset))));
			baselinePath.strokeColor=settings.baselineColor;
			baselinePath.strokeWidth=2;
			baselineArray = baselinePath.segments.map( s => toIntXY(s.point.divide(scalingFactor)));
			baselineArray = baselineArray.map( pt => truncate_point( pt, charter.width, charter.height));
		}

		return { 'contourPath': contourPath, 'baselinePath': baselinePath, data: { 'id': id, 'centerline': centerlineArray, 'baseline': baselineArray, 'boundary': boundaryArray, 'strokeWidth': p.strokeWidth, 'baselineOffset': p.baselineOffset } }
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
		mode = Modes.normal;
	}


	/* exposed functions */
	return { 
		exportMask: exportMask, 
		importMask: importMask, 
		previewMaskOn: previewMaskOn,
		eraseMask: eraseMask,
		applySettings: applySettings,
		getSetting: getSetting, 
	}

}

