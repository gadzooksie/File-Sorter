#ifndef FILE_SORTER_MENU_BRIDGE_H
#define FILE_SORTER_MENU_BRIDGE_H
/* The only toplevel X11 window belongs to File-Sorter-Launcher. Each application
   is an actual child window of that shell, and processes carry on when hidden. */
#include <X11/Xlib.h>
#include <X11/Xatom.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
static Window fs_menu_launcher=None;
static Window fs_menu_parent(Display *display){
    const char *raw=getenv("FILE_SORTER_EMBED_PARENT");
    if(!raw||!*raw)return RootWindow(display,DefaultScreen(display));
    errno=0;char *end=NULL;unsigned long n=strtoul(raw,&end,0);
    if(errno||!end||*end||!n)return RootWindow(display,DefaultScreen(display));
    fs_menu_launcher=(Window)n;
    return fs_menu_launcher;
}
static void fs_menu_register(Display *display,Window child,const char *slot){
    if(fs_menu_launcher==None)return;
    Atom prop=XInternAtom(display,slot,False);
    unsigned long id=(unsigned long)child;
    XChangeProperty(display,fs_menu_launcher,prop,XA_WINDOW,32,PropModeReplace,(unsigned char*)&id,1);
    XFlush(display);
}
static int fs_menu_show(Display *display,Window child){
    if(fs_menu_launcher==None)return 0;
    XEvent event={0};
    event.xclient.type=ClientMessage;
    event.xclient.display=display;
    event.xclient.window=fs_menu_launcher;
    event.xclient.message_type=XInternAtom(display,"FILE_SORTER_NAVIGATE",False);
    event.xclient.format=32;
    event.xclient.data.l[0]=0; /* menu */
    event.xclient.data.l[1]=(long)child;
    XSendEvent(display,fs_menu_launcher,False,NoEventMask,&event);
    XFlush(display);
    return 1;
}
#endif
