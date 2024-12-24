paper.install(window);

window.onload = function(){
	var canvas = document.getElementById("myCanvas");
	console.log("Before setup:");
	console.log( canvas);

	paper.setup(canvas);
	console.log("After setup:");
	console.log(canvas);


	
	console.log(img_file);
	//img = '096ee892464c3efb69d622953d1033ad.img.jpg';
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
	
	paths = [];

	var pathDrawingMode = false;

	view.onDoubleClick = (ev) => {
		/*if (this.changed_img){
			console.log("Image has changed.");
			//update_image( this.img_file );
			//this.changed_img = false;
		}*/
		
		console.log(ev.point);
		if (pathDrawingMode){
			pathDrawingMode = false;
			paths[paths.length-1].isSelected=false;
			return;
		} else {
			pathDrawingMode = true;
			var path = new Path() ;
			path.strokeColor = 'red';
			path.strokeWidth = 4;
			path.strokeCap = 'round';
			path.strokeJoin = 'round';
			path.isSelected = false;
			paths.push( path );
			console.log(path);
			paths[paths.length-1].add( ev.point ) ;
			console.log( paths );
		};
	}

	view.onClick = (ev) => {
		paths.forEach( (p) => {
			if (p.hitTest( ev.point ) !== null){
				console.log("Path is selected!");
				p.isSelected = true;
			}
		})
		if (Key.isDown('a')){
			paths.forEach( (p) => {
				console.log("Path is selected!");
				p.isSelected = true;
			})
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
		}
	}
	
	view.onMouseDown = (ev) => {
		if (pathDrawingMode && paths.length > 0){
			var path = paths[paths.length-1].add(ev.point);
		}
	}


}

