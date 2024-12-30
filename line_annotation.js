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
 * 	- cancel last action (use JSON export)
 *
 * TODO:
 * 	- modes should be exclusive of each other, with a single mode variable
 */

paper.install(window);

window.onload = function(){
	var canvas = document.getElementById("myCanvas");
	paper.setup(canvas);
	
	var charter = null;

	canvas.update_img = function update_image( img ){
		charter = new Raster( img );
		//scaling_factor = canvas.width/charter.width;
		//charter.scale( scaling_factor) ;
		charter.position = view.center;
		charter.fitBounds( view.bounds );
		view.draw();
		this.changed_img = false;
	}

	canvas.update_img( this.img_file );
	
	var paths = [];
	var currentPath = null;
	var currentSegmentIndex = -1;
	var currentSegmentHandle = null;

	var pathDrawingMode = false;
	var segmentEditMode = false;

	view.onDoubleClick = (ev) => {
		
		if (pathDrawingMode){
			pathDrawingMode = false;
			selectPath(paths[paths.length-1], false);
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
		} else if (Key.isDown('<')){
			paths.forEach( (p) => { 
				p.strokeWidth -= (1*p.isSelected);
			})
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
			}
		}
	}
	
	view.onMouseDown = (ev) => {
		console.log("MouseDown:");
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
			}
		}
	}	

	view.onMouseDrag = (ev) => { 
		// move the path node
		segmentEditMode = true;
		if (currentSegmentIndex >= 0){
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

