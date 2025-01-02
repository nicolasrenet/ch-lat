/* nprenet@gmail.com, 12/2024
 *
 * Drawing tool for annotating charters.
 *
 * Interface:
 *
 * Selection mode
 * 	- click to select a path		✓
 * 	- Alt-click anywhere selects all paths  ✓
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
 * 		+ color selection	  ✓
 * 		+ drag to move it         ✓
 * 		+ 'd' to delete it        ✓ 
 * 	- Ctrl-click to select a stroke and add a segment on it ✓
 * 	 
 * History:
 * 	- save history after:
 * 		+ segment or path addition
 * 		+ segment move
 * 	- cancel last N actions (use JSON export) x (buggy)
 *
 * Masks:
 * 	- export baseline mask
 * 	- export polygon mask
 *
 * TODO:
 * 	- modes should be exclusive of each other, with a single mode variable
 */

paper.install(window);


window.onload = function(){

	var canvas = document.getElementById("myCanvas");

	paper.setup(canvas);
	
	var charter = null;
	var charterLayer = new Layer();
	var annotationLayer = new Layer();
	var exportLayer = new Layer();


	canvas.update_img = function update_image( img ){
		charterLayer.activate();
		charter = new Raster( img );
		//scaling_factor = canvas.width/charter.width;
		//charter.scale( scaling_factor) ;
		console.log( "scaling_factor = " + canvas.width/charter.width);
		charter.position = view.center;
		charter.fitBounds( view.bounds );
		view.draw();
		//this.changed_img = false;
		annotationLayer.activate();
	}

	console.log( this.img_file )
	canvas.update_img( this.img_file );
	
	var paths = [];
	var rasterPaths = [];
	var currentPath = null;
	var currentSegmentIndex = -1;
	var currentSegmentHandle = null;

	var pathDrawingMode = false;
	var segmentEditMode = false;

	var history = [null,null,null,null,null];
	var HISTLENGTH = 5;
	var historyCount = 0;

	// Initial state
	historySave();

	annotationLayer.activate()

	function historySave( op ){
		//console.log("historySave()");
		history[historyCount++]=op;
	}

	function historyRestore(){
		console.log("historyRestore(): history.length = " + history.filter( (h) => h !== null ).length )
		thisOpIndex = (historyCount-1) % HISTLENGTH
		previousOpIndex = (thisOpIndex - 1 + HISTLENGTH) % HISTLENGTH
		console.log("historyRestore(): thisOpIndex = " + thisOpIndex + ", previousOpIndex = " + previousOpIndex );
		previousOp = history[previousOpIndex];
		if (previousOp !== null){
			//paper.project.importSVG( previousOp.svg );
			history[thisOpIndex]=null;
			historyCount--;
			console.log("Restored " + paths.length + " paths.");
		}
		segmentEditMode = false;
		pathDrawingMode = false;
	}


	function exportMask(){

		var Marker = function (pt) {
			this.p = Path.Circle( pt, 2 );
			this.p.fillColor='red';
		};

		var toIntXY = function ( pt ){
		    	return [ Math.round(pt.x), Math.round(pt.y)]
		}

		var contour = function (p){

		    	var pointsNorth = []
		    	var pointsSouth = []
		    	var contourPath = new Path();
		    	//contourPath.strokeColor='#000000'
		    	//contourPath.strokeWidth=2;

		    	var pt1 = p.segments[0].point
		    	var pt2 = p.segments[1].point        
		    	var vect = (pt2.subtract(pt1)).normalize( p.strokeWidth/2)
		    	var endPt1 = pt1.subtract(vect);
		    	var normalVect = vect.rotate(90)
		    	contourPath.add( pt1.add(normalVect))
		    	contourPath.insert(0, pt1.subtract(normalVect))

		    	var pt3 = p.segments.at(-2).point
		    	var pt4 = p.segments.at(-1).point        
		    	var vectEnd = (pt4.subtract(pt3)).normalize( p.strokeWidth/2)
		    	var endPt2 = pt4.add(vectEnd);
		    	var normalVectEnd = vectEnd.rotate(90)

		    	if (p.segments.length > 2){

				for (var i=1; i<p.segments.length-1; i++){
			    	var pt = p.segments[i].point
			    	var ptL = p.segments[i-1].point        
			    	var ptR = p.segments[i+1].point        
			    	var vectL = (ptL.subtract(pt)).normalize( p.strokeWidth/2)
			    	var vectR = (ptR.subtract(pt)).normalize( p.strokeWidth/2)
			    	var normalVect = vectL.subtract(vectR).divide(2).rotate(90)
			    	contourPath.insert(0, pt.add(normalVect))
			    	contourPath.add(pt.subtract(normalVect))
				}
		    	}
		    	contourPath.add( pt4.add(normalVectEnd))
		    	contourPath.insert(0, pt4.subtract(normalVectEnd))
		    	contourPath.insert( contourPath.segments.length/2, endPt1)
		    	contourPath.add( endPt2 )
		    	contourPath.closed = true;
		    	contourPath.smooth({type: 'geometric'})
		    
		    	contourPath.selected = true;
		    
		    	// adding points along curves
		    	//console.log(contourPath.curves)
		    	var path = []
		    	for (const s of p.segments){
				path.push( toIntXY(s.point))
		    	}
		    	var polygon = [];
		    	for (const c of contourPath.curves){
				polygon.push( toIntXY(c.point1));
				var midPoint1 = c.getPointAt( c.length/3 );
				var midPoint2 = c.getPointAt( c.length*2/3 );
				polygon.push( toIntXY(midPoint1))
				polygon.push( toIntXY(midPoint2))
				polygon.push( toIntXY(c.point2));

				var intermMark1 = new Marker(midPoint1)
				var intermMark2 = new Marker(midPoint2)
		    	}
			contourPath.selected=true;

		    	return {
				'path': path,
				'polygon': polygon
		    	}
		}


		var toExport = []
		for (const p of paths){
			toExport.push( contour( p ));
		}
		console.log(toExport);
		return toExport

	}

	view.onDoubleClick = (ev) => {
		
		if (pathDrawingMode){
			pathDrawingMode = false;
			//paths[paths.length-1].smooth({type: 'geometric'});
			selectPath(paths[paths.length-1], false);
			historySave();
			console.log(history[historyCount%HISTLENGTH-1]);
		} else {
			pathDrawingMode = true;
			var path = new Path() ;
			path.strokeColor = 'red';
			path.strokeWidth = 4;
			path.strokeCap = 'round';
			path.strokeJoin = 'round';
			selectPath(path, false);
			paths.push( path );
			paths[paths.length-1].add( ev.point ) ;
		};
	}

	view.onClick = (ev) => {
		console.log("segmentEditMode=" + segmentEditMode);
		// append a segment to a path
		if (pathDrawingMode && paths.length > 0){
			paths[paths.length-1].add(ev.point);
			return;
		}
		// after dragging/moving a node 
		if (segmentEditMode){
			segmentEditMode = false;
			currentPath = null;
			currentSegmentIndex = -1;
			historySave();
		}
		// select all paths
		if (ev.modifiers.alt){
			paths.forEach( (p) => {
				selectPath( p, true );
			});
			return
		}
		// select one path
		pathHitResult = getHitPath( ev.point );
		if (pathHitResult !== null){
			var p = pathHitResult.item;
			selectPath( p, true );
			paths.forEach( (op) => {
				if (op === p){ return }
				selectPath( op, false );
			});
		// or nothing
		} else {
			paths.forEach( (p) => {
				selectPath( p, false );
			});
		}
	}

	view.onKeyDown = (ev) => {
		if (Key.isDown('>')) {
			paths.forEach( (p) => { 
				console.log(p.isSelected)
				p.strokeWidth += (1*p.isSelected);
			})
			historySave();
		} else if (Key.isDown('<')){
			paths.forEach( (p) => { 
				p.strokeWidth -= (1*p.isSelected);
			})
			historySave();
		} else if (Key.isDown('escape')){
			pathDrawingMode = false;
			segmentEditMode = false;
			paths.forEach( (p) => {
				selectPath(p, false);
			});
		} else if (Key.isDown('d')){
			if (currentPath !== null && currentSegmentIndex > -1){
				currentPath.removeSegment( currentSegmentIndex );
				currentPath = null;
				currentSegmentIndex = -1;
				if (currentSegmentHandle !== null){
					currentSegmentHandle.remove();
				}
				historySave();
			}
		} else if (ev.modifiers.control && Key.isDown('z')){ // buggy
			console.log('Ctrl-z');
			historyRestore();
		} else if (ev.modifiers.control && Key.isDown('s')){
			console.log('Ctrl-s');
			exportMask();
		}
	}
	
	view.onMouseDown = (ev) => {
		//console.log("MouseDown:");
		var pathHitResult = getHitPath( ev.point );
		// Edit a segment
		if (! pathDrawingMode && pathHitResult !== null && (pathHitResult.type === 'segment' || pathHitResult.type==='stroke')){
			currentPath = pathHitResult.item;
			// clicking on a path node (="Segment") makes this node editable (drag)
			if (pathHitResult.type === 'segment'){
				console.log( pathHitResult.segment);
				currentSegmentIndex = pathHitResult.segment.index;
				// visual feedback after hitting the node
				currentSegmentHandle = new Path.Circle({ radius: 4, center: pathHitResult.segment.point, fillColor: 'red'});
			// ctrl-clicking on a path stroke adds a node in the given position
			} else if ( pathHitResult.type === 'stroke' && ev.modifiers.control ){
				currentSegmentIndex = pathHitResult.location.curve.segment2.index;
				currentPath.insert( currentSegmentIndex, ev.point );
				historySave();
			}
		}
	}	

	view.onMouseDrag = (ev) => { 
		// move the path node
		if (currentSegmentIndex >= 0){
			segmentEditMode = true;
			var segt = currentPath.segments[currentSegmentIndex]
			currentSegmentHandle.remove();
			currentPath.removeSegment( currentSegmentIndex )
			currentPath.insert( currentSegmentIndex, segt.point.x+ev.delta.x, segt.point.y+ev.delta.y);
		}
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
		for (var p=0; p<paths.length; p++){
			hitResult = paths[p].hitTest( pt );
			if (hitResult !== null){ break }
		}
		return hitResult;
	}

}

