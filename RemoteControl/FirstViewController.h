//
//  FirstViewController.h
//  RemoteControl
//
//  Created by Albert Zeyer on 14.03.11.
//  Copyright 2011 __MyCompanyName__. All rights reserved.
//

#import <UIKit/UIKit.h>


@interface FirstViewController : UIViewController
<UITableViewDataSource> {
	IBOutlet UIButton* playButton;
	IBOutlet UITableView* pyOutput;
}

- (IBAction) playPressed;
- (IBAction) prevPressed;
- (IBAction) nextPressed;
- (IBAction) volUpPressed;
- (IBAction) volDownPressed;
- (IBAction) reconnectPressed;

@end
