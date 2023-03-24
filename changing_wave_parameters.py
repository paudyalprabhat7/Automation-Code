from plxscripting.easy import *
import subprocess, time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import datetime

#PLAXIS path
PLAXIS_PATH = r'C:\Program Files\Bentley\Geotechnical\PLAXIS 3D CONNECT Edition V21\Plaxis3DInput.exe'

PORT_i = 10000 #defining a port number
PORT_o = 10001 

PASSWORD = 'Pr@bhatASU9#'

#opening PLAXIS 3D
subprocess.Popen([PLAXIS_PATH, f'--AppServerPassword={PASSWORD}', f'--AppServerPort={PORT_i}'], shell=False)

#waiting for PLAXIS 3D to boot
time.sleep(5)

#starting the scripting server
s_i, g_i = new_server('localhost', PORT_i, password = PASSWORD)
s_o, g_o = new_server('localhost', PORT_o, password = PASSWORD)

def initialize(a):
    s_i.new()

    #set project length unit to mm
    g_i.setproperties('UnitLength', 'mm')

    #create rectangular geometry
    g_i.SoilContour.initializerectangular(-a/2, -a/2, a/2, a/2)

    #create borehole
    g_i.borehole(0, 0)

    #create soillayer
    g_i.soillayer(10000.0)
    g_i.set(g_i.Borehole_1.Head, -10000.0)

def createsoilmat(matval):
    #create a sample material
    matprop = ['MaterialName', 'SoilModel', 'Gref', 'cref', 'phi', 'gammaUnsat', 'gammaSat', 'nu', 'InterfaceStrength', 'Rinter', 'RayleighAlpha', 'RayleighBeta']
    material_data = list(zip(matprop, matval))
    return g_i.soilmat(*material_data)

def createpointdisp():
    #go to structure mode
    g_i.gotostructures()

    #define a point
    Point_1 = g_i.point(0.0, 0.0, 0.0)

    #createPointDisplacement
    g_i.pointdispl(Point_1)

    #fix x and y directions
    g_i.Point_1.PointDisplacement.Displacement_x = 'fixed'
    g_i.Point_1.PointDisplacement.Displacement_y = 'fixed'

    #prescribe z displacement
    g_i.Point_1.PointDisplacement.Displacement_z = 'Prescribed'

    #static component
    g_i.Point_1.PointDisplacement.uz = -1.0

    #dynamic component
    DisplacementMultiplier_1 = g_i.displmultiplier()

    g_i.Point_1.PointDisplacement.PointDisplacement.Multiplierz = DisplacementMultiplier_1

def setpointdisp(amp,freq): 
    g_i.DisplacementMultiplier_1.Amplitude = amp
    g_i.DisplacementMultiplier_1.Frequency = freq

def createmesh():
    #meshing_procedure
    g_i.gotomesh()
    #g_i.set(g_i.Line_1_1.CoarsenessFactor, 0.0175)
    g_i.mesh("Coarseness", 0.025, "UseEnhancedRefinements", True, "EMRGlobalScale", 1.2, "EMRMinElementSize", 0.005, "UseSweptMeshing", False)
    g_i.viewmesh()
    g_i.selectmeshpoints()
    #add curve points for plotting
    #g_o.addcurvepoint('Node', 0.0,0.0, -1000.0)
    depths = np.linspace(1000.0, 9000.0, num = 9)
    for i in range(len(depths)):
        g_o.addcurvepoint('Node', (0.0,0.0,-depths[i]))
    g_o.update()
   
def stagedconstruct(amp, freq):
    #going to structures and assigning materials and assigning surf_displacement
    g_i.gotostructures()
    
    #set material to soil volume
    g_i.setmaterial(g_i.Soillayer_1.Soil, g_i.Sand)

    #set material to geophone
    #g_i.setmaterial(g_i.Line_1.EmbeddedBeam, g_i.Geophone)

    #set dynamic multipliers of the displacement
    setpointdisp(amp, freq)
    
    #staged construction and defining initial phases
    g_i.gotostages()
    g_i.phase(g_i.InitialPhase)
    g_i.phase(g_i.Phase_1)
    g_i.phase(g_i.Phase_2)
    
    #defining phase 1
    #g_i.EmbeddedBeam_1_1.activate(g_i.Phase_1)

    #defining phase 2
    g_i.set(g_i.Phase_2.DeformCalcType, 'Dynamic')
    g_i.set(g_i.Phase_2.Deform.TimeIntervalSeconds, 0.5)
    g_i.set(g_i.Phase_2.Deform.ResetDisplacementsToZero, True)
    g_i.set(g_i.Phase_2.Deform.UseDefaultIterationParams, False)
    g_i.set(g_i.Phase_2.Deform.ToleratedError, 0.05)
    g_i.set(g_i.Phase_2.Deform.TimeStepDetermType, 'Manual')
    g_i.PointDisplacement_1_1.activate(g_i.Phase_2)
    g_i.DynPointDisplacement_1_1.activate(g_i.Phase_2)
    g_i.Dynamics.BoundaryXMin[g_i.Phase_2] = "None"
    g_i.Dynamics.BoundaryYMin[g_i.Phase_2] = "None"
    g_i.Dynamics.BoundaryZMin[g_i.Phase_2] = "Viscous"

    #defining phase 3
    g_i.set(g_i.Phase_3.DeformCalcType, 'Dynamic')
    g_i.set(g_i.Phase_3.Deform.TimeIntervalSeconds, 0.5)
    g_i.set(g_i.Phase_3.Deform.UseDefaultIterationParams, False)
    g_i.set(g_i.Phase_3.Deform.ToleratedError, 0.05)
    g_i.set(g_i.Phase_3.Deform.TimeStepDetermType, 'Manual')
    g_i.PointDisplacement_1_1.deactivate(g_i.Phase_3)
    g_i.DynPointDisplacement_1_1.deactivate(g_i.Phase_3)
    g_i.Dynamics.BoundaryXMin[g_i.Phase_3] = "None"
    g_i.Dynamics.BoundaryYMin[g_i.Phase_3] = "None"
    g_i.Dynamics.BoundaryZMin[g_i.Phase_3] = "Viscous"

def getgraphsoil(node):
    g_i.view(g_i.InitialPhase)
    stepids = []
    uz = []
    times = []
    phasenames = []
    phaseorder = [g_o.Phase_2, g_o.Phase_3]

    for phase in phaseorder:
        for step in phase.Steps.value:
            phasenames.append(phase.Name.value)
            stepids.append(int(step.Name.value.replace("Step_", "")))
            uz.append(g_o.getcurveresults(g_o.Nodes[node],
                                          step,
                                          g_o.ResultTypes.Soil.Uz))
            timevalue = "-"
            if hasattr(step, 'Reached'):
                if hasattr(step.Reached, 'Time'):
                    timevalue = step.Reached.Time.value
            times.append(timevalue)
        
    values = np.linspace(0, 0.1, num=200)
    timestep = pd.Series(values, index=range(200))
    df = pd.DataFrame()
    df['t (sec)'] = timestep
    df['z (mm)'] = pd.Series(uz)

    plt.style.reload_library()
    plt.style.use(['grid', 'science', 'notebook'])
    x = df['t (sec)'].tolist()
    y = df['z (mm)'].tolist()

    plt.figure(facecolor='white')
    plt.plot(x, y)
    plt.xlabel('Dynamic Time (sec)')
    plt.ylabel('Vertical Displacement, Uz (mm)')

    min_y = min(y)
    plt.axhline(min_y, color='red', linestyle='--')
    #plt.yticks(np.append(plt.yticks()[0], min_y))
    plt.tick_params(axis='x', which='major', pad=10)
    plt.tick_params(axis='y', which='major', pad=10)
    
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d_%H%M")
    filename = "graph_withoutbeam" + date_str
    directory = "D:\\Plaxis Automation Codes\\Graphs\\withandwithoutbeam"

    if not os.path.exists(directory):
        os.makedirs(directory)

    plt.savefig(os.path.join(directory, filename + ".png"), dpi=300)
    plt.show()

def timehistsoil(node):
    stepids = []
    uz = []
    vz = []
    az = []
    times = []
    phasenames = []
    phaseorder = [g_o.Phase_2, g_o.Phase_3]

    for phase in phaseorder:
        for step in phase.Steps.value:
            phasenames.append(phase.Name.value)
            stepids.append(int(step.Name.value.replace("Step_", "")))
            uz.append(g_o.getcurveresults(g_o.Nodes[node],
                                            step,
                                            g_o.ResultTypes.Soil.Uz))
            vz.append(g_o.getcurveresults(g_o.Nodes[node],
                                            step,
                                            g_o.ResultTypes.Soil.Vz))
            az.append(g_o.getcurveresults(g_o.Nodes[node], step, g_o.ResultTypes.Soil.Az))
            timevalue = "-"
            if hasattr(step, 'Reached'):
                if hasattr(step.Reached, 'Time'):
                    timevalue = step.Reached.Time.value
            times.append(timevalue)
        
    values = np.linspace(0, 0.1, num=200)
    timestep = pd.Series(values, index=range(200))
    df = pd.DataFrame()
    df['t (sec)'] = timestep
    df['z (mm)'] = pd.Series(uz)
    df['v (mm/sec)'] = pd.Series(vz)
    df['a (mm2/sec)'] = pd.Series(az)

    return df

def savefile(stry):
      # Get the current date and time
    now = datetime.datetime.now()

    # Format the date and time as a string in the format YYYY-MM-DD_HH:MM:SS
    date_str = now.strftime("%Y-%m-%d")

    # Append "graph_" to the beginning of the date string
    filename = "test_nobeam" + stry + date_str

    # Set the directory for saving the file
    directory = "D:\\Plaxis Automation Codes\\withandwithoutbeam\\withbeaminterface"

    # Create the directory if it doesn't exist
    if not os.path.exists(directory):
        os.makedirs(directory)

    g_i.save(os.path.join(directory,filename))

def calculateval():
    g_i.calculate()

def getmaxval(node):
    maximum = g_o.getcurveresults(g_o.curvePoints.Nodes[node], g_o.Phase_2, g_o.ResultTypes.Soil.Uz, "min")
    maximum = maximum * -1.0
    return maximum
    
iterations2 = [1000.0, 2000.0, 3000.0, 4000.0, 5000.0, 6000.0, 7000.0, 8000.0, 9000.0]
results = []

#geophone_mat = ['Geophone', 0, 0, 0, 0, 30, 200, 7.65e-8, 30, 0.1, 0.1, 706.858347057703, 39760.7820219958, 39760.7820219958, 0, 100]
amp = np.linspace(10.0, 100.0, n=10)
freq = np.linspace(1.0, 15.0, n=15)
hor_ext = 3000
mat = ['Sand', 2, 0.0192307692307692, 5e-6, 28.0, 2e-8, 2e-8, 0.3, 1, 0.667, 3.11, 0.00079577]

for i in range(len(amp)):
    for j in range(len(freq)):
        initialize(hor_ext)
        createsoilmat(mat)
        createpointdisp()
        createmesh()
        stagedconstruct(amp[i], freq[j])
        calculateval()
        g_i.view(g_i.InitialPhase)

        # Create a workbook object
        excel_path = 'D:\\Automation Code\\timehistories\\'+'amplitude_'+str(amp[i])+'mm_'+str(freq[j])+'_hz'+'loc_origin'+'.xlsx'
        writer = pd.ExcelWriter(excel_path)

        # Loop through nodes 0 to 8
        for node in range(9):
            # Call the timehistsoil function for the current node
            df = timehistsoil(node)
            
            # Write the dataframe to a separate sheet within the workbook
            sheet_name = 'node_' + str(node+1) + ' m'
            df.to_excel(writer, sheet_name=sheet_name, index=False)

        # Save the workbook
        writer.save()