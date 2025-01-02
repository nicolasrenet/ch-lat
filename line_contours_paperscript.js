annotation = new Layer()
annotation.activate();

var strokeWidth = 20
var p1 = new Path.Line(new Point(20,40), new Point(300,80))
p1.strokeColor='#add8e6'
p1.strokeWidth=strokeWidth

p1.addSegments([ new Point(550,60), new Point(700,25)])

function contour(p){

var pointsNorth = []
var pointsSouth = []
var contourPath = new Path();
contourPath.strokeColor='#000000'
contourPath.strokeWidth=2;

var pt1 = p.segments[0].point
var mark1 = new Path.Circle(pt1, 5)
mark1.strokeWidth=4
mark1.strokeColor='green'

var pt2 = p1.segments[1].point        
var mark2 = new Path.Circle( pt2, 5)
mark2.strokeWidth=4
mark2.strokeColor='green'

var vect = (pt2-pt1).normalize( strokeWidth/2)
var endPt1 = pt1-vect;
var normalVect = vect.rotate(90)
contourPath.add( pt1 + normalVect)
var markS = new Path.Circle( pt1+normalVect, 2)
markS.strokeWidth=2
markS.strokeColor='green'
contourPath.insert(0, pt1 - normalVect)
var markN = new Path.Circle( pt1-normalVect, 2)
markN.strokeWidth=2
markN.strokeColor='red'


var pt3 = p.segments.at(-2).point
var mark3 = new Path.Circle(pt3, 5)
mark3.strokeWidth=4
mark3.strokeColor='green'

var pt4 = p.segments.at(-1).point        
var mark4 = new Path.Circle( pt4, 5)
mark4.strokeWidth=4
mark4.strokeColor = 'green'

var vectEnd = (pt4-pt3).normalize( strokeWidth/2)
var endPt2 = pt4+vectEnd;
var normalVectEnd = vectEnd.rotate(90)

var markSE = new Path.Circle( pt4+normalVectEnd, 2)
markSE.strokeWidth=2
markSE.strokeColor='green'

var markNE = new Path.Circle( pt4-normalVectEnd, 2)
markNE.strokeWidth=2
markNE.strokeColor='red'

if (p.segments.length > 2){

for (var i=1; i<p.segments.length-1; i++){
    var pt = p.segments[i].point
    var m = new Path.Circle(pt, 5)
    m.strokeWidth=4
    m.strokeColor='green'
    var ptL = p.segments[i-1].point        
    var mL = new Path.Circle( ptL, 5)
    mL.strokeWidth=4
    mL.strokeColor='green'
    var ptR = p.segments[i+1].point        
    var mR = new Path.Circle( ptR, 5)
    mR.strokeWidth=4
    mR.strokeColor='green'

    var vectL = (ptL-pt).normalize( strokeWidth/2)
    var vectR = (ptR-pt).normalize( strokeWidth/2)

    var normalVect = ((vectL-vectR)/2).rotate(90)
        //contourPath.add( pt1 + normalVect)
    var markN = new Path.Circle( pt+normalVect, 2)
    markN.strokeWidth=2
    markN.strokeColor='red'
    var markS = new Path.Circle( pt-normalVect, 2)
    markS.strokeWidth=2
    markS.strokeColor='green'
    contourPath.insert(0, pt+normalVect)
    contourPath.add(pt-normalVect)

}
}
contourPath.add( pt4 + normalVectEnd)
contourPath.insert(0, pt4 - normalVectEnd)
contourPath.insert( contourPath.segments.length/2, endPt1)
contourPath.add( endPt2 )
contourPath.closed = true;
contourPath.smooth({type: 'geometric'})

    
}

contour(p1)
//raster = p1.rasterize()
//raster.position.x += 50



