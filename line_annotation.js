paper.install(window);

/*
 * Desirable features:
 * + remove entire path 
 * + edit mode for one path:  (Ctrl-E)
 *   + delete end-segment (?)
 *   + add internal node (middle-click)
 *   + move existing node (click/select point + drag)
 */

window.onload = function(){
	var canvas = document.getElementById("myCanvas");
	console.log("Before setup:");
	console.log( canvas);

	paper.setup(canvas);
	console.log("After setup:");
	console.log(canvas);


	
	console.log(img_file);
	charter = null;

	canvas.update_img = function update_image( img ){
		console.log("line_annotation.js: update_image()")
		charter = new Raster( img );
		//scaling_factor = canvas.width/charter.width;
		//charter.scale( scaling_factor) ;
		charter.position = view.center;
		charter.fitBounds( view.bounds );
		view.draw();
		this.changed_img = false;
	}

	canvas.update_img( this.img_file );
	
	console.log( canvas );
	
	var paths = [];
	var currentPath = null;
	var currentSegment = 0;

	var pathDrawingMode = false;
	var segmentEditMode = false;

	view.onDoubleClick = (ev) => {
		
		console.log(ev.point);
		if (pathDrawingMode){
			console.log("DoubleClick: pathDrawingMode -> false");
			pathDrawingMode = false;
			selectPath(paths[paths.length-1], false);
		} else {
			console.log("DoubleClick: pathDrawingMode -> true");
			pathDrawingMode = true;
			var path = new Path() ;
			path.strokeColor = 'red';
			path.strokeWidth = 4;
			path.strokeCap = 'round';
			path.strokeJoin = 'round';
			selectPath(path, false);
			paths.push( path );
			console.log("DoubleClick:" + path);
			paths[paths.length-1].add( ev.point ) ;
			console.log("DoubleClick:"+ paths );
		};
	}

	view.onClick = (ev) => {
		console.log("Clik: segmentEditMode = " + segmentEditMode + ", pathDrawingMode = " + pathDrawingMode)
		if (pathDrawingMode && paths.length > 0){
			paths[paths.length-1].add(ev.point);
			return;
		}
		if (segmentEditMode){
			console.log("Click: segmentEditMode -> false")
			//this.requestUpdate()
			segmentEditMode = false;
			currentPath = null;
			currentSegment = -1;
			//return
		}
		pathHitResult = getHitPath( ev.point );
		if (pathHitResult !== null){
			console.log(pathHitResult)
			var p = pathHitResult.item;
			console.log("OnClick:" + p);
			selectPath( p, true );
			paths.forEach( (op) => {
				if (op === p){ return }
				selectPath( op, false );
			});
		} else {
			paths.forEach( (p) => {
				selectPath( p, false );
			});
		}
		if (Key.isDown('a')){
			paths.forEach( (p) => {
				console.log("Path is selected!");
				selectPath( p, true );
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
		}
	}
	
	view.onMouseDown = (ev) => {
		console.log("MouseDown:");
		var pathHitResult = getHitPath( ev.point );
		console.log(pathHitResult);
		if (! pathDrawingMode && pathHitResult !== null && (pathHitResult.type === 'segment' || pathHitResult.type==='stroke')){
			currentPath = pathHitResult.item;
			console.log("OnMouseDown: parent path = " + currentPath );
			if (pathHitResult.type === 'segment'){
				currentSegment = pathHitResult.segment.index;
				console.log("OnMouseDown: segment object = " + currentSegment );
			} else if ( pathHitResult.type === 'stroke' ){
				currentSegment = pathHitResult.location.curve.segment2.index;
			}
			//console.log("OnMouseDown: segment object " + p.segments[hitResult.segment.index]);
			segmentEditMode = true;
			console.log("segmentEditMode -> true");
			if (pathHitResult.type === 'stroke'){
				console.log("current path length = " + currentPath.length)
				currentPath.insert( currentSegment, ev.point );
				console.log("current path length = " + currentPath.length)
				console.log(currentPath);
			}
		}
	}	

	view.onMouseDrag = (ev) => { 
		segt = currentPath.segments[currentSegment]
		console.log("Current segment before: " + segt )
		if (segmentEditMode){
			currentPath.removeSegment( currentSegment )
			console.log('delta='+ev.delta)
			currentPath.insert( currentSegment, segt.point.x+ev.delta.x, segt.point.y+ev.delta.y);
			console.log("Current segment after: "+currentPath.segments[currentSegment]);
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
		console.log("getHitPath(" + pt + ")");
		console.log(paths);
		var hitResult = null;
		for (var p=0; p<paths.length; p++){
			hitResult = paths[p].hitTest( pt );
			if (hitResult !== null){ break }
		}
		return hitResult;
	}

}

